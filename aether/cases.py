"""Assemble complete, self-contained case directories (mesh + configs + metadata)."""
from __future__ import annotations

import json
import math
import os
import re
from dataclasses import asdict
from typing import Optional

import yaml

from .conditions import freestream_from_T0, freestream_from_Tinf, freestream_from_pT, summary_dict
from .geometry import CapsuleParams, build_profile, check_profile, export_csv, export_json, InvalidGeometry
from .mesh import capsule_mesh, CapsuleMeshSpec, cylinder_mesh, CylinderMeshSpec, write_su2_wedge
from .su2config import CaseSettings, write_stage_configs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONDITIONS = os.path.join(ROOT, "configs", "conditions.yaml")


def _floats(d):
    if isinstance(d, dict):
        return {k: _floats(v) for k, v in d.items()}
    if isinstance(d, str):
        try:
            return float(d) if re.fullmatch(r"[-+]?[\d.]+[eE][-+]?\d+", d) else d
        except ValueError:
            return d
    return d


def load_conditions(path: str = CONDITIONS) -> dict:
    with open(path) as fh:
        return _floats(yaml.safe_load(fh))


def main_freestream(cond: Optional[dict] = None):
    cond = cond or load_conditions()
    m = cond["main"]
    return freestream_from_T0(m["name"], m["mach"], m["T0"], m["Re_D"], m["D"], m["T_wall"])


def cylinder_freestream(cond: Optional[dict] = None):
    cond = cond or load_conditions()
    c = cond["cylinder"]
    return freestream_from_pT(c["name"], c["mach"], c["p_inf"], c["T_inf"], c["radius"], c["T_wall"])


def build_cylinder_case(case_dir: str, level: str = "medium", spec_overrides: Optional[dict] = None,
                        settings_overrides: Optional[dict] = None) -> dict:
    cond = load_conditions()
    c = cond["cylinder"]
    os.makedirs(case_dir, exist_ok=True)
    spec = CylinderMeshSpec(level=level, radius=c["radius"], **(spec_overrides or {}))
    mesh = cylinder_mesh(spec)
    mesh.write_su2(os.path.join(case_dir, "mesh.su2"))
    rep = mesh.write_report(os.path.join(case_dir, "mesh_report.json"))
    mesh.plot(os.path.join(case_dir, "mesh.png"), title=f"cylinder {level}")
    mesh.plot(os.path.join(case_dir, "mesh_zoom.png"), zoom=(-0.06, 0.0, 0.0, 0.06), title=f"cylinder {level} (near wall)")
    settings = CaseSettings(kind="cylinder", mach=c["mach"], p_inf=c["p_inf"], T_inf=c["T_inf"],
                            T_wall=c["T_wall"], ref_length=c["radius"], ref_area=2.0 * c["radius"],
                            **(settings_overrides or {}))
    write_stage_configs(settings, case_dir)
    meta = {"kind": "cylinder", "level": level, "conditions": c, "mesh_spec": asdict(spec),
            "settings": asdict(settings), "mesh_quality": rep["quality"]}
    with open(os.path.join(case_dir, "case.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    return meta


def build_capsule_case(case_dir: str, params: CapsuleParams, level: str = "medium",
                       spec_overrides: Optional[dict] = None, settings_overrides: Optional[dict] = None,
                       case_id: str = "", group: str = "", phase: int = 0) -> dict:
    """Returns metadata. Raises InvalidGeometry for shapes that fail the
    geometric validity rules (the caller records the failure)."""
    cond = load_conditions()
    fs = main_freestream(cond)
    os.makedirs(case_dir, exist_ok=True)
    prof = build_profile(params)
    issues = check_profile(prof)
    if issues:
        raise InvalidGeometry("; ".join(issues))
    export_json(prof, os.path.join(case_dir, "geometry.json"))
    export_csv(prof, os.path.join(case_dir, "profile.csv"))
    spec = CapsuleMeshSpec(level=level, **{"truncate_at_base": True, **(spec_overrides or {})})
    mesh = capsule_mesh(params, spec)
    q = mesh.quality()
    if q["n_negative_area"] > 0:
        raise InvalidGeometry(f"mesh has {q['n_negative_area']} inverted cells")
    wedge = None
    if spec.wedge_layers > 0:
        mesh.write_su2(os.path.join(case_dir, "mesh2d.su2"))      # the meridional mesh (wall nodes, plots)
        wedge = write_su2_wedge(mesh, os.path.join(case_dir, "mesh.su2"), spec.wedge_layers, spec.wedge_deg)
    else:
        mesh.write_su2(os.path.join(case_dir, "mesh.su2"))
    rep = mesh.write_report(os.path.join(case_dir, "mesh_report.json"))
    if wedge:
        rep["wedge"] = wedge
        with open(os.path.join(case_dir, "mesh_report.json"), "w") as fh:
            json.dump(rep, fh, indent=2)
    mesh.plot(os.path.join(case_dir, "mesh.png"), title=f"{case_id or params.label()} {level}")
    L = prof.length
    mesh.plot(os.path.join(case_dir, "mesh_zoom.png"), zoom=(-0.4 * params.D, L + 0.5 * params.D, 0.0, 1.1 * params.D),
              title=f"{case_id or params.label()} {level} (near body)")
    D = params.D
    A_ref = math.pi * D * D / 4.0
    if wedge:
        kind = "capsule_wedge"
        A_su2 = A_ref * spec.wedge_deg / 360.0        # the wedge carries this fraction of the body
        defaults = {"run_stage2": True, "s1_iter": 4000}
    else:
        kind = "capsule_truncated" if spec.truncate_at_base else "capsule"
        A_su2 = A_ref
        defaults = {"run_stage2": False, "s1_iter": 4000}
    settings = CaseSettings(kind=kind, mach=fs.mach, p_inf=fs.p_inf, T_inf=fs.T_inf,
                            T_wall=fs.T_wall, ref_length=D, ref_area=A_su2,
                            **{**defaults, **(settings_overrides or {})})
    write_stage_configs(settings, case_dir)
    meta = {"kind": "capsule", "case_id": case_id, "group": group, "phase": phase, "level": level, "params": asdict(params),
            "freestream": summary_dict(fs, params.Rn), "mesh_spec": asdict(spec),
            "settings": asdict(settings), "mesh_quality": rep["quality"],
            "geometry": {"length_m": prof.length, "volume_m3": prof.volume, "wetted_area_m2": prof.wetted_area,
                         "s_P1": prof.s_P1, "s_Pmax": prof.s_Pmax, "s_P2": prof.s_P2, "s_P3": prof.s_P3,
                         "s_Pf": prof.s_Pf, "s_P4": prof.s_P4, "shield_arc_length_m": prof.s_P2},
            "mass_nominal_kg": cond["main"]["mass_nominal"], "A_ref_m2": A_ref, "wedge": wedge}
    with open(os.path.join(case_dir, "case.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    return meta


def baseline_params() -> CapsuleParams:
    cond = load_conditions()
    m = cond["main"]
    return CapsuleParams(D=m["D"], Rn_D=8.32 / 6.92, Rs_D=0.35 / 6.92, theta_c_deg=33.0, rb_D=m["rb_D"], rf_D=m["rf_D"])
