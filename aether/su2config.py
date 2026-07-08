"""Render SU2 configuration files from configs/su2_template.cfg.

Every case is run as a sequence of stages on the same mesh, each restarting
from the previous one (docs/validation.md A.2-A.4 for the evidence behind
this procedure):

  stage 1  start-up: Roe flux with a large entropy fix (0.3), first order,
           adaptive CFL 0.5 -> 30 from a uniform free stream. This scheme is
           free of the carbuncle instability and establishes the bow shock
           and the overall field reliably; its boundary-layer heat flux is
           not usable (the fix dissipates the entropy and shear waves).
  stage 2  analysis stage: SLAU2 with the exact flux Jacobian, first order,
           restarted from stage 1, adaptive CFL 1 -> 30. Started from the
           established field it converges to the carbuncle-free steady
           state at every mesh level tested; started from a uniform free
           stream it can lock into the carbuncle branch on refined meshes.
           All capsule results are taken from this stage.
  stage 3  (planar benchmark only) second-order MUSCL reconstruction with
           the Venkatakrishnan-Wang limiter, restarted from stage 2, fixed
           CFL 1.5. In axisymmetric mode this stage never reaches a
           stationary state with SU2 v8.5 (A.4), so it is not run for the
           capsule; on the cylinder it quantifies the order effect.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Dict

TEMPLATE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "configs", "su2_template.cfg")

BC_LINES = {
    "capsule": "MARKER_SYM= ( axis )\nMARKER_FAR= ( farfield )",
    "capsule_truncated": "MARKER_SYM= ( axis )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
    "capsule_wedge": "MARKER_SYM= ( symmetry_left, symmetry_right )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
    "cylinder": "MARKER_SYM= ( symmetry )\nMARKER_FAR= ( farfield )\nMARKER_SUPERSONIC_OUTLET= ( outflow )",
}

# per-stage numerical settings
STAGES = {
    1: dict(conv_scheme="ROE", entropy_fix="0.3", accurate_jac="NO", muscl="NO", limiter="VENKATAKRISHNAN_WANG",
            cfl="0.5", cfl_adapt="YES", cfl_min="0.5", cfl_max="10.0", restart_sol="NO"),
    2: dict(conv_scheme="SLAU2", entropy_fix="0.0", accurate_jac="YES", muscl="NO", limiter="VENKATAKRISHNAN_WANG",
            cfl="1.0", cfl_adapt="YES", cfl_min="1.0", cfl_max="30.0", restart_sol="YES"),
    3: dict(conv_scheme="SLAU2", entropy_fix="0.0", accurate_jac="YES", muscl="YES", limiter="VENKATAKRISHNAN_WANG",
            cfl="1.5", cfl_adapt="NO", cfl_min="1.5", cfl_max="1.5", restart_sol="YES"),
}


@dataclass
class CaseSettings:
    kind: str                     # key of BC_LINES
    mach: float
    p_inf: float
    T_inf: float
    T_wall: float
    ref_length: float
    ref_area: float
    mesh: str = "mesh.su2"
    n_stages: int = 2             # capsule: 2 (first-order analysis); cylinder: 3
    venkat: float = 0.05
    iters: Dict[int, int] = field(default_factory=lambda: {1: 2500, 2: 4000, 3: 4000})
    cauchy_eps: Dict[int, float] = field(default_factory=lambda: {1: 5e-5, 2: 2e-5, 3: 2e-5})
    conv_resid: float = -10.0
    wrt_freq: int = 500
    extra: Dict[str, str] = field(default_factory=dict)        # KEY -> value appended to every stage ("__DELETE__" removes)
    stage_extra: Dict[int, Dict[str, str]] = field(default_factory=dict)   # per-stage overrides

    @property
    def axisymmetric(self) -> str:
        return "YES" if self.kind in ("capsule", "capsule_truncated") else "NO"


def _apply_overrides(text: str, overrides: Dict[str, str]) -> str:
    lines = text.splitlines()
    for k, v in overrides.items():
        lines = [ln for ln in lines if not ln.startswith(k + "=")]
        if v != "__DELETE__":
            lines.append(f"{k}= {v}")
    return "\n".join(lines) + "\n"


def _render(settings: CaseSettings, stage: int) -> str:
    with open(TEMPLATE) as fh:
        tpl = fh.read()
    st = STAGES[stage]
    values = dict(
        axisymmetric=settings.axisymmetric,
        mach=f"{settings.mach:.4f}",
        p_inf=f"{settings.p_inf:.6g}",
        T_inf=f"{settings.T_inf:.6g}",
        T_wall=f"{settings.T_wall:.4f}",
        ref_length=f"{settings.ref_length:.8g}",
        ref_area=f"{settings.ref_area:.10g}",
        bc_lines=BC_LINES[settings.kind],
        venkat=f"{settings.venkat:g}",
        mesh=settings.mesh,
        wrt_freq=str(settings.wrt_freq),
        iter=str(settings.iters[stage]),
        cauchy_eps=f"{settings.cauchy_eps[stage]:g}",
        conv_resid=f"{settings.conv_resid:g}",
        solution_in=f"restart_stage{stage - 1}.dat" if stage > 1 else "restart_stage0.dat",
        restart_out=f"restart_stage{stage}.dat",
        history=f"history_stage{stage}", volume=f"flow_stage{stage}", surface=f"surface_stage{stage}",
        breakdown=f"forces_stage{stage}.dat",
        **st,
    )
    out = tpl
    for k, v in values.items():
        out = out.replace("{" + k + "}", v)
    out = _apply_overrides(out, settings.extra)
    out = _apply_overrides(out, settings.stage_extra.get(stage, {}))
    body = "\n".join(ln for ln in out.splitlines() if not ln.startswith("%"))
    leftover = re.findall(r"\{[a-z_0-9]+\}", body)
    if leftover:
        raise ValueError(f"unfilled placeholders: {sorted(set(leftover))}")
    return out


def write_stage_configs(settings: CaseSettings, case_dir: str) -> Dict[int, str]:
    os.makedirs(case_dir, exist_ok=True)
    paths = {}
    for stage in range(1, settings.n_stages + 1):
        path = os.path.join(case_dir, f"stage{stage}.cfg")
        with open(path, "w") as fh:
            fh.write(_render(settings, stage))
        paths[stage] = path
    return paths
