"""Command-line driver:  python -m aether <command> [options]

  conditions            write docs/conditions.md from configs/conditions.yaml
  geometry              write the baseline profile, SVG sketch and parameter table to docs/
  benchmark-cyl         build and run the Wieting cylinder on coarse/medium/fine
  baseline              build and run the baseline capsule on coarse/medium/fine
  domain-check          baseline (medium) with a larger far boundary
  sweep                 run every case in configs/sweep.yaml (resumable)
  post                  post-process all case directories -> results/results.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import traceback

from .cases import (ROOT, build_capsule_case, build_cylinder_case, baseline_params,
                    load_conditions, main_freestream, cylinder_freestream)
from .conditions import summary_dict, fay_riddell_stagnation
from .geometry import CapsuleParams, InvalidGeometry, build_profile, export_svg, export_csv, export_json
from .postproc import postprocess_case
from .runner import run_case

CASES = os.path.join(ROOT, "cases")
RESULTS = os.path.join(ROOT, "results")
DOCS = os.path.join(ROOT, "docs")


def log(msg: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


def cmd_conditions(args):
    cond = load_conditions()
    fs = main_freestream(cond)
    cyl = cylinder_freestream(cond)
    c = cond["cylinder"]
    lines = ["# Operating conditions", "",
             "All simulations: calorically perfect air (gamma 1.4, R 287.058 J/kg/K), Sutherland viscosity "
             "(mu_ref 1.716e-5 Pa s at 273.15 K, S 110.4 K), laminar, constant Prandtl number 0.72. "
             "Densities and pressures are what SU2 computes from the Mach number, static pressure and "
             "static temperature given in the configuration files.", "",
             "## Main study condition (capsule family) — Benchmark B", "",
             f"Clean Apollo CM in AEDC Tunnel C (NASA TM X-1243): M = {fs.mach}, Re_D = {fs.Re_ref:.2e}, D = {fs.ref_length:.5f} m "
             f"(0.045-scale model). Stagnation temperature taken as {fs.T0:.1f} K (1900 R), within the facility "
             "envelope of 1650-1950 R; the report does not quote the run's T0. Cold isothermal wall at 300 K.", "",
             fs.table_markdown(), "",
             f"Fay-Riddell stagnation-point heat flux estimate for the baseline nose radius (R_n = {baseline_params().Rn:.4f} m): "
             f"{fay_riddell_stagnation(fs, baseline_params().Rn)/1e3:.1f} kW/m^2 (perfect gas, Le = 1, Newtonian velocity gradient). "
             "This is a sanity check for the order of magnitude, not validation data.", "",
             "## Benchmark A (solver heating check, planar) — Wieting Run 31", "",
             f"Calspan 48-inch HST, undisturbed 3-inch cylinder (NASA TM 100484, Table 11, Run 31): M = {c['mach']}, "
             f"p_inf = {c['p_inf']:.1f} Pa (0.124 psia), T_inf = {c['T_inf']} K (224.9 R), wall {c['T_wall']} K (530 R). "
             "Given p and T directly, SU2's Sutherland viscosity yields the Reynolds number below; the report's "
             "value is 1.468e6 /ft = 4.816e6 /m (1.835e5 on the radius), 2 % lower than Sutherland.", "",
             cylinder_freestream_table(c), "",
             "## Limits of the gas model", "",
             "- Freestream static temperatures are 49 K (main) and 125 K (cylinder); Sutherland's law is "
             "extrapolated below its usual 100 K lower limit for the main condition. Near the body the gas is at "
             "post-shock temperatures (up to T0), where the law is well within range.",
             "- Post-shock stagnation temperatures of 1056 K (main) and 1736 K (cylinder, perfect gas) excite "
             "molecular vibration; Wieting reports T_T = 1583 K for Run 31 from the thermally perfect tunnel "
             "calibration. Dissociation is negligible at both conditions. The calorically perfect assumption "
             "therefore over-predicts post-shock temperature by a few percent for the main condition and by about "
             "10 % for the cylinder; this is a stated limitation of the heating comparison.",
             "- No turbulence model: both reference experiments report laminar flow at these Reynolds numbers.",
             ]
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, "conditions.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(DOCS, "conditions_main.json"), "w") as fh:
        json.dump(summary_dict(fs, baseline_params().Rn), fh, indent=2)
    log("wrote docs/conditions.md")


def cylinder_freestream_table(c) -> str:
    from .conditions import freestream_from_Tinf, sutherland, R_AIR, speed_of_sound, pitot_pressure_ratio
    T, p, M = c["T_inf"], c["p_inf"], c["mach"]
    rho = p / (R_AIR * T); U = M * speed_of_sound(T); mu = sutherland(T)
    Re_R = rho * U * c["radius"] / mu
    rows = [("Mach number", f"{M}", "-"), ("Static temperature", f"{T}", "K"), ("Static pressure", f"{p:.1f}", "Pa"),
            ("Density", f"{rho:.5f}", "kg/m^3"), ("Velocity", f"{U:.1f}", "m/s"), ("Viscosity (Sutherland)", f"{mu:.3e}", "Pa s"),
            ("Reynolds number on radius 0.0381 m", f"{Re_R:.3e}", "-"), ("Pitot pressure (Rayleigh)", f"{p*pitot_pressure_ratio(M):.0f}", "Pa"),
            ("Report P0 (Run 31)", f"{c['P0']:.0f}", "Pa"), ("Report Q0 (Run 31)", f"{c['Q0']:.3e}", "W/m^2"),
            ("Wall temperature", f"{c['T_wall']}", "K")]
    return "\n".join(["| Quantity | Value | Unit |", "|---|---:|---|"] + [f"| {a} | {b} | {c_} |" for a, b, c_ in rows])


def cmd_geometry(args):
    p = baseline_params()
    prof = build_profile(p)
    os.makedirs(DOCS, exist_ok=True)
    export_svg(prof, os.path.join(DOCS, "figure_geometry_baseline.svg"), "AETHER capsule family: baseline parameters")
    export_csv(prof, os.path.join(DOCS, "baseline_profile.csv"))
    export_json(prof, os.path.join(DOCS, "baseline_geometry.json"))
    log(f"baseline: L/D={prof.length/p.D:.4f} V={prof.volume:.6e} m^3 s_P1/R={prof.s_P1/p.R:.4f} s_Pmax/R={prof.s_Pmax/p.R:.4f}")


RETRY_SCHEDULES = [   # alternative stage-2 schedules tried when the first SLAU2 stage lands on the carbuncle branch
    {"CFL_ADAPT": "NO", "CFL_NUMBER": "1.0"},
    {"CFL_ADAPT": "YES", "CFL_NUMBER": "0.5", "CFL_ADAPT_PARAM": "( 0.5, 1.2, 0.5, 5.0, 1e-3, 0 )"},
    {"CFL_ADAPT": "NO", "CFL_NUMBER": "0.5"},
]


def _run_and_post(case_dir, nproc):
    from .runner import run_stage
    from .su2config import _apply_overrides
    rec = run_case(case_dir, nproc=nproc)
    out = postprocess_case(case_dir)
    attempt = 0
    while out.get("physical_branch") is False and attempt < len(RETRY_SCHEDULES) and os.path.exists(os.path.join(case_dir, "stage2.cfg")):
        # keep the failed attempt's evidence, then retry stage 2 from the same stage-1 state
        tag = f"attempt{attempt}"
        for f in ("history_stage2.csv", "summary_stage2.json", "stage2.log", "run_stage2.json", "stage2.cfg"):
            if os.path.exists(os.path.join(case_dir, f)):
                os.replace(os.path.join(case_dir, f), os.path.join(case_dir, f.replace("stage2", f"stage2_{tag}")))
        with open(os.path.join(case_dir, f"stage2_{tag}.cfg")) as fh:
            cfg = fh.read()
        with open(os.path.join(case_dir, "stage2.cfg"), "w") as fh:
            fh.write(_apply_overrides(cfg, RETRY_SCHEDULES[attempt]))
        log(f"{case_dir}: carbuncle branch (p_stag/pitot={out.get('p_stag_over_pitot'):.3f}, q_axis/plateau={out.get('q_axis_over_plateau'):.2f}); retry {attempt + 1} with {RETRY_SCHEDULES[attempt]}")
        run_stage(case_dir, 2, nproc=nproc)
        out = postprocess_case(case_dir)
        out["stage2_attempts"] = attempt + 2
        with open(os.path.join(case_dir, "summary.json"), "w") as fh:
            json.dump(out, fh, indent=2)
        attempt += 1
    log(f"{case_dir}: status={out.get('status')} CD={out.get('cd')} qmax={out.get('q_max_shield', out.get('q_max'))} p/pitot={out.get('p_stag_over_pitot')}")
    return out


def cmd_benchmark_cyl(args):
    for level in args.levels:
        d = os.path.join(CASES, "benchmarks", "wieting_cyl", level)
        if args.skip_done and os.path.exists(os.path.join(d, "summary.json")):
            log(f"skip {d}"); continue
        build_cylinder_case(d, level)
        _run_and_post(d, args.nproc)


def cmd_baseline(args):
    for level in args.levels:
        d = os.path.join(CASES, "baseline", level)
        if args.skip_done and os.path.exists(os.path.join(d, "summary.json")):
            log(f"skip {d}"); continue
        build_capsule_case(d, baseline_params(), level, case_id="B00" if level == "coarse" else f"B00_{level}", group="baseline")
        _run_and_post(d, args.nproc)


def cmd_domain_check(args):
    checks = {"base_far": {"d_far_nose_D": 3.0, "d_far_wake_D": 7.0}}
    for name, spec in checks.items():
        d = os.path.join(CASES, "domain_check", name)
        if args.skip_done and os.path.exists(os.path.join(d, "summary.json")):
            log(f"skip {d}"); continue
        build_capsule_case(d, baseline_params(), "coarse", case_id=f"B00_{name}", group="check", spec_overrides=spec)
        _run_and_post(d, args.nproc)


def cmd_sweep(args):
    import yaml
    with open(os.path.join(ROOT, "configs", "sweep.yaml")) as fh:
        sw = yaml.safe_load(fh)
    level = args.level or sw["mesh_level"]
    base = baseline_params()
    failures = os.path.join(RESULTS, "invalid_cases.csv")
    os.makedirs(RESULTS, exist_ok=True)
    for c in sw["cases"]:
        if args.phase and int(c.get("phase", 1)) != args.phase:
            continue
        if c.get("enabled") is False:
            continue
        if args.only and c["id"] not in args.only:
            continue
        d = os.path.join(CASES, "sweep", c["id"])
        if args.skip_done and os.path.exists(os.path.join(d, "summary.json")):
            log(f"skip {c['id']}"); continue
        params = CapsuleParams(D=base.D, Rn_D=float(c["Rn_D"]), Rs_D=float(c["Rs_D"]),
                               theta_c_deg=float(c["theta_c"]), rb_D=base.rb_D)
        try:
            build_capsule_case(d, params, level, case_id=c["id"], group=c.get("group", ""), phase=int(c.get("phase", 1)))
        except InvalidGeometry as e:
            log(f"{c['id']}: INVALID geometry: {e}")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "invalid.json"), "w") as fh:
                json.dump({"case_id": c["id"], "params": params.__dict__, "reason": str(e)}, fh, indent=2)
            continue
        try:
            _run_and_post(d, args.nproc)
        except Exception:
            log(f"{c['id']}: run failed\n" + traceback.format_exc())


def cmd_refine(args):
    """Re-run selected sweep cases on finer levels (ranking stability of the finalists)."""
    import yaml
    with open(os.path.join(ROOT, "configs", "sweep.yaml")) as fh:
        sw = yaml.safe_load(fh)
    base = baseline_params()
    table = {c["id"]: c for c in sw["cases"]}
    table[sw["baseline"]["id"]] = {**sw["baseline"], "group": "baseline"}
    for cid in args.ids:
        c = table[cid]
        params = CapsuleParams(D=base.D, Rn_D=float(c["Rn_D"]), Rs_D=float(c["Rs_D"]), theta_c_deg=float(c["theta_c"]), rb_D=base.rb_D)
        for level in args.levels:
            d = os.path.join(CASES, "refine", f"{cid}_{level}")
            if args.skip_done and os.path.exists(os.path.join(d, "summary.json")):
                log(f"skip {d}"); continue
            build_capsule_case(d, params, level, case_id=f"{cid}_{level}", group="refine", phase=3)
            _run_and_post(d, args.nproc)


def cmd_fields(args):
    """ParaView field figures for the baseline and the designs named in results/pareto_analysis.json."""
    import subprocess
    pv = "/Applications/ParaView-6.2.0.app/Contents/bin/pvpython"
    picks = {"baseline": os.path.join(CASES, "baseline", "coarse")}
    pa = os.path.join(RESULTS, "pareto_analysis.json")
    if os.path.exists(pa):
        with open(pa) as fh:
            a = json.load(fh)
        import pandas as pd
        res = pd.read_csv(os.path.join(RESULTS, "results.csv"))
        for lab, cid in (("highest_drag", a["highest_drag"]), ("lowest_heating", a["lowest_heating"]),
                         ("compromise", (a["selections"].get("lowest_q_at_98pct_drag") or {}).get("case_id"))):
            if cid and cid != "B00":
                r = res[res["case_id"] == cid]
                if not r.empty:
                    picks[f"{lab}_{cid}"] = r["case_dir"].iloc[0]
    os.makedirs(os.path.join(RESULTS, "figures", "fields"), exist_ok=True)
    for lab, d in picks.items():
        out = os.path.join(RESULTS, "figures", "fields", lab)
        cmd = [pv, os.path.join(ROOT, "scripts", "paraview_fields.py"), d, out] + (["--revolve"] if lab == "baseline" else [])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        log(f"fields {lab}: exit {r.returncode} {r.stderr.strip().splitlines()[-1][:120] if r.returncode else ''}")


def cmd_tables(args):
    """Markdown tables for the report -> results/tables.md"""
    import pandas as pd
    res = pd.read_csv(os.path.join(RESULTS, "results.csv"))
    L = ["# Result tables (generated by `python -m aether tables`)", ""]
    cap = res[res["kind"] == "capsule"].copy()
    def f(v, fmt):
        try:
            return fmt.format(v) if v == v else "—"
        except Exception:
            return "—"
    # 1. every capsule case
    L += ["## All capsule cases", "", "| case | group | level | R_n/D | R_s/D | θ_c [°] | L/D | status | stage-2 attempts | C_D | q''_max shield [kW/m²] | S/R of q''_max | q'' plateau [kW/m²] | p_stag/pitot | stand-off / D |",
          "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|"]
    for _, r in cap.sort_values(["group", "case_id", "level"]).iterrows():
        L.append(f"| {r['case_id']} | {r.get('group','')} | {r['level'] if r['level']==r['level'] else '—'} | {f(r['Rn_D'],'{:.3f}')} | {f(r['Rs_D'],'{:.4f}')} | {f(r['theta_c_deg'],'{:.0f}')} | {f(r['length_D'],'{:.3f}')} | {r['status']} | {f(r.get('stage2_attempts', float('nan')),'{:.0f}') if r.get('stage2_attempts', float('nan')) == r.get('stage2_attempts', float('nan')) else '1'} | {f(r['cd'],'{:.4f}')} | {f(r['q_max_shield']/1e3 if r['q_max_shield']==r['q_max_shield'] else float('nan'),'{:.1f}')} | {f(r['s_over_R_q_max'],'{:.3f}')} | {f(r['q_plateau']/1e3 if r['q_plateau']==r['q_plateau'] else float('nan'),'{:.1f}')} | {f(r['p_stag_over_pitot'],'{:.3f}')} | {f(r['shock_standoff_D'],'{:.3f}')} |")
    # 2. section-8 summary table
    pa = os.path.join(RESULTS, "pareto_analysis.json")
    if os.path.exists(pa):
        with open(pa) as fh:
            a = json.load(fh)
        sel = (a["selections"].get("lowest_q_at_98pct_drag") or {}).get("case_id")
        cols = {"Baseline": "B00", "Highest-drag case": a["highest_drag"], "Lowest-heating case": a["lowest_heating"], "Selected compromise": sel}
        rows = {}
        for lab, cid in cols.items():
            r = cap[(cap["case_id"] == cid)]
            rows[lab] = r.iloc[0] if not r.empty else None
        L += ["", "## Summary table (Section 8 of the project plan)", "", "| Metric | " + " | ".join(cols.keys()) + " |", "|---|" + "---:|" * len(cols)]
        def row(name, key, fmt, scale=1.0):
            L.append(f"| {name} | " + " | ".join(f(rows[k][key] * scale, fmt) if rows[k] is not None else "—" for k in cols) + " |")
        L.append("| Case id | " + " | ".join(str(c) for c in cols.values()) + " |")
        row("Nose radius R_n/D", "Rn_D", "{:.3f}"); row("Rear-body cone angle θ_c [°]", "theta_c_deg", "{:.0f}"); row("Shoulder radius R_s/D", "Rs_D", "{:.4f}")
        row("Drag coefficient C_D", "cd", "{:.4f}"); row("Drag force [N] (model scale)", "drag_N", "{:.1f}"); row("Peak heat flux on shield [kW/m²]", "q_max_shield", "{:.1f}", 1e-3)
        row("Peak-heating location S/R", "s_over_R_q_max", "{:.3f}"); row("Shock stand-off / D", "shock_standoff_D", "{:.3f}")
        L.append("| Mesh/convergence checks passed? | " + " | ".join(("yes" if rows[k] is not None and rows[k]["status"] == "converged" else "no") for k in cols) + " |")
    with open(os.path.join(RESULTS, "tables.md"), "w") as fh:
        fh.write("\n".join(L) + "\n")
    log("wrote results/tables.md")


def cmd_post(args):
    rows = []
    for root, dirs, files in os.walk(CASES):
        if "case.json" in files:
            try:
                rows.append(postprocess_case(root))
            except Exception as e:
                rows.append({"case_dir": root, "status": f"postproc_error: {e}"})
        elif "invalid.json" in files:
            with open(os.path.join(root, "invalid.json")) as fh:
                inv = json.load(fh)
            rows.append({"case_dir": root, "case_id": inv["case_id"], "kind": "capsule", "status": "invalid_geometry", "group": "invalid",
                         "Rn_D": inv["params"]["Rn_D"], "Rs_D": inv["params"]["Rs_D"],
                         "theta_c_deg": inv["params"]["theta_c_deg"], "invalid_reason": inv["reason"]})
    cols = ["case_id", "group", "phase", "kind", "level", "status", "Rn_D", "Rs_D", "theta_c_deg", "length_D", "volume_m3",
            "n_cells", "binary", "nproc", "su2_version", "iterations", "wall_time_s",
            "rms_rho_drop_orders", "cd_flatness", "maxhf_flatness", "q_max_change_last_window", "physical_branch",
            "p_stag_over_pitot", "q_axis_over_plateau", "stage2_attempts", "converged", "convective_order",
            "cd", "cd_integrated", "cd_pressure_integrated", "drag_N", "drag_over_mass",
            "q_stag", "q_plateau", "q_max_shield", "s_q_max_shield", "s_over_R_q_max", "q_axis_region_max", "q_axis_region_min", "q_max_whole_body", "s_q_max_whole_body",
            "q_max", "theta_q_max", "p_stag", "shock_standoff_m", "shock_standoff_D", "invalid_reason", "case_dir"]
    extra = sorted({k for r in rows for k in r} - set(cols))
    os.makedirs(RESULTS, exist_ok=True)
    rows.sort(key=lambda r: (r.get("kind", ""), r.get("case_id", ""), r.get("level", "")))
    with open(os.path.join(RESULTS, "results.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + extra)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols + extra})
    log(f"wrote results/results.csv with {len(rows)} rows")


def cmd_uncertainty(args):
    """Richardson/GCI on the baseline levels and the shock-spacing check -> results/uncertainty.json,
    docs/mesh_convergence.md table."""
    import pandas as pd
    from .convergence import gci, two_grid_uncertainty
    res = pd.read_csv(os.path.join(RESULTS, "results.csv"))
    out = {"quantities": {}}
    def pick(cid):
        r = res[res["case_id"] == cid]
        return None if r.empty else r.iloc[0]
    lv = {k: pick(c) for k, c in (("coarse", "B00"), ("medium", "B00_medium"), ("fine", "B00_fine"))}
    cyl = {k: res[(res["kind"] == "cylinder") & (res["level"] == k)] for k in ("coarse", "medium", "fine")}
    far = pick("B00_base_far")
    lines = ["# Mesh convergence and domain checks (baseline)", "",
             "Levels refine the boundary layer by r = 1.5 (docs/mesh.md). GCI after Celik et al. (2008), Fs = 1.25 for a monotone triplet, else p = 1 and Fs = 3.", "",
             "| Quantity | coarse | medium | fine | observed order p | extrapolated | GCI medium | GCI coarse |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    if all(v is not None for v in lv.values()):
        for q, label in (("cd", "C_D"), ("q_max_shield", "q''_max shield [W/m^2]"), ("q_stag", "q''_stag (axis node) [W/m^2]"), ("q_plateau", "q'' at S/R = 0.2 [W/m^2]"), ("q_shoulder", "q'' shoulder peak [W/m^2]"), ("shock_standoff_D", "shock stand-off / D")):
            vals = {}
            for k, r in lv.items():
                if q in ("q_plateau", "q_shoulder"):
                    w = pd.read_csv(os.path.join(r["case_dir"], "wall_profile.csv"))
                    with open(os.path.join(r["case_dir"], "case.json")) as fh:
                        meta = json.load(fh)
                    R = 0.5 * meta["params"]["D"]; sP1, sP2 = meta["geometry"]["s_P1"], meta["geometry"]["s_P2"]
                    import numpy as np
                    if q == "q_plateau":
                        vals[k] = float(np.interp(0.2 * R, w["s"], w["Heat_Flux"]))
                    else:
                        m = (w["s"] >= 0.9 * sP1) & (w["s"] <= sP2)
                        vals[k] = float(w["Heat_Flux"][m].max())
                else:
                    vals[k] = float(r[q]) if r[q] == r[q] else None
            if any(v is None for v in vals.values()):
                continue
            g = gci(vals["fine"], vals["medium"], vals["coarse"], r=1.5)
            out["quantities"][q] = {**vals, **{kk: g[kk] for kk in ("p", "monotone", "f_extrapolated", "GCI_fine", "GCI_medium")}, "GCI_coarse": g["GCI_medium"] * (1.5 ** g["p_used"])}
            lines.append(f"| {label} | {vals['coarse']:.5g} | {vals['medium']:.5g} | {vals['fine']:.5g} | {g['p']:.2f}" if g["p"] else f"| {label} | {vals['coarse']:.5g} | {vals['medium']:.5g} | {vals['fine']:.5g} | n/a (non-monotone)")
            lines[-1] += f" | {g['f_extrapolated']:.5g} | {100*g['GCI_medium']:.2f} % | {100*out['quantities'][q]['GCI_coarse']:.2f} % |"
    lines += ["", "## Domain check (coarse level)", "", "| Check | C_D | Δ C_D | q''_max shield | Δ q''_max |", "|---|---:|---:|---:|---:|"]
    base = lv["coarse"]
    checks = {}
    if base is not None:
        for name, r in (("far boundary 3.0 D / 7.0 D", far),):
            if r is None: continue
            dcd = abs(r["cd"] / base["cd"] - 1.0); dq = abs(r["q_max_shield"] / base["q_max_shield"] - 1.0)
            checks[name] = {"cd": float(r["cd"]), "d_cd_rel": float(dcd), "q_max_shield": float(r["q_max_shield"]), "d_q_rel": float(dq)}
            lines.append(f"| {name} | {r['cd']:.4f} | {100*dcd:.2f} % | {r['q_max_shield']:.0f} | {100*dq:.2f} % |")
    out["checks"] = checks
    # uncertainty for the trade space: larger of base-level GCI and the shock-spacing sensitivity
    conv = res[(res["kind"] == "capsule") & (res["status"] == "converged")]
    snap = float(conv["q_max_change_last_window"].max()) if "q_max_change_last_window" in conv and len(conv) else 0.0
    cdflat = float(conv["cd_flatness"].max()) if len(conv) else 0.0
    out["max_snapshot_change_q"] = snap; out["max_cd_flatness"] = cdflat
    u_cd = max([out["quantities"].get("cd", {}).get("GCI_coarse", 0.0), cdflat] + [c["d_cd_rel"] for c in checks.values()])
    u_q = max([out["quantities"].get("q_max_shield", {}).get("GCI_coarse", 0.0), snap] + [c["d_q_rel"] for c in checks.values()])
    out["u_cd"] = float(u_cd); out["u_q"] = float(u_q)
    lines += ["", f"Uncertainty used in the trade-space analysis (coarse level): u_CD = {100*u_cd:.2f} %, u_q = {100*u_q:.2f} % (largest of the coarse-level GCI, the far-boundary sensitivity and the largest residual non-stationarity among converged sweep cases: drag {100*cdflat:.2f} %, peak heating {100*snap:.2f} % between the last two snapshots)."]
    # cylinder table
    if all(not v.empty for v in cyl.values()):
        lines += ["", "## Cylinder benchmark levels", "", "| Level | cells | C_D (1st order) | q''_stag (1st) [W/m^2] | C_D (2nd) | q''_stag (2nd) | q''_stag / Q_0 (2nd) |", "|---|---:|---:|---:|---:|---:|---:|"]
        for k, r in cyl.items():
            r = r.iloc[0]
            b = os.path.join(r["case_dir"], "benchmark_cylinder.json")
            s1 = json.load(open(os.path.join(r["case_dir"], "summary_stage1.json"))) if os.path.exists(os.path.join(r["case_dir"], "summary_stage1.json")) else {}
            lines.append(f"| {k} | {int(r['n_cells'])} | {s1.get('cd', float('nan')):.4f} | {s1.get('q_stag', float('nan')):.0f} | {r['cd']:.4f} | {r['q_stag']:.0f} | {r['q_stag']/721050:.3f} |")
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "uncertainty.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    with open(os.path.join(DOCS, "mesh_convergence.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote results/uncertainty.json and docs/mesh_convergence.md")


def cmd_figures(args):
    import pandas as pd
    from . import plots
    from .pareto import analyse, sensitivities
    from .benchmarks import cylinder_comparison, apollo_comparison
    res = pd.read_csv(os.path.join(RESULTS, "results.csv"))
    made = []
    cyl = {lv: os.path.join(CASES, "benchmarks", "wieting_cyl", lv) for lv in ("coarse", "medium", "fine")
           if os.path.exists(os.path.join(CASES, "benchmarks", "wieting_cyl", lv, "wall_profile.csv"))}
    if cyl:
        made.append(plots.cylinder_validation(cyl))
        for lv, d in cyl.items():
            cylinder_comparison(d)
    base = {lv: os.path.join(CASES, "baseline", lv) for lv in ("coarse", "medium", "fine")
            if os.path.exists(os.path.join(CASES, "baseline", lv, "wall_profile.csv"))}
    if base:
        made.append(plots.apollo_validation(base))
        for lv, d in base.items():
            apollo_comparison(d)
        made.append(plots.mesh_study(res, "B00"))
        for lv, d in base.items():
            made.append(plots.convergence_history(d, f"convergence_baseline_{lv}.png"))
    conv = res[(res["kind"] == "capsule") & (res["status"] == "converged")]
    if (conv["case_id"] == "B00").any() and len(conv) > 2:
        unc = {}
        unc_path = os.path.join(RESULTS, "uncertainty.json")
        if os.path.exists(unc_path):
            with open(unc_path) as fh:
                unc = json.load(fh)
        analysis, df = analyse(res, u_cd=unc.get("u_cd", 0.0), u_q=unc.get("u_q", 0.0))
        df.to_csv(os.path.join(RESULTS, "tradespace.csv"), index=False)
        with open(os.path.join(RESULTS, "pareto_analysis.json"), "w") as fh:
            json.dump(analysis, fh, indent=2, default=str)
        made.append(plots.pareto_plot(df, analysis, u_cd=unc.get("u_cd", 0.0), u_q=unc.get("u_q", 0.0)))
        sens = sensitivities(df)
        sens.to_csv(os.path.join(RESULTS, "sensitivities.csv"), index=False)
        made.append(plots.sensitivity_plot(sens))
        picks = {"baseline": "B00", "highest drag": analysis["highest_drag"], "lowest heating": analysis["lowest_heating"]}
        sel = analysis["selections"].get("lowest_q_at_98pct_drag")
        if sel:
            picks["selected compromise"] = sel["case_id"]
        dirs = {}
        for lab, cid in picks.items():
            row = df[df["case_id"] == cid]
            if not row.empty:
                dirs[f"{lab} ({cid})"] = row["case_dir"].iloc[0]
        made.append(plots.wall_distributions(dirs))
    for m in made:
        log(f"wrote {os.path.relpath(m, ROOT)}")


def cmd_versions(args):
    import subprocess
    from .runner import pick_binary, su2_version
    binary, flavour = pick_binary()
    lines = ["# Software versions used", "",
             f"- SU2: {su2_version(binary)} ({flavour}), binary `{os.path.relpath(binary, ROOT)}`",
             f"- Python: {sys.version.split()[0]} (`{sys.executable}`)"]
    for mod in ("numpy", "scipy", "pandas", "matplotlib", "gmsh", "vtk", "yaml", "meshio"):
        try:
            m = __import__(mod)
            lines.append(f"- {mod}: {getattr(m, '__version__', getattr(m, 'VTK_VERSION', '?'))}")
        except Exception as e:
            lines.append(f"- {mod}: not importable ({e})")
    for cmd, label in (("mpirun --version", "Open MPI"), ("/Applications/ParaView-6.2.0.app/Contents/bin/pvpython --version", "ParaView"),
                       ("sw_vers -productVersion", "macOS"), ("sysctl -n machdep.cpu.brand_string", "CPU")):
        try:
            outp = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=30)
            lines.append(f"- {label}: {(outp.stdout or outp.stderr).strip().splitlines()[0]}")
        except Exception as e:
            lines.append(f"- {label}: unavailable ({e})")
    with open(os.path.join(DOCS, "versions.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    log("wrote docs/versions.md")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aether")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("conditions").set_defaults(fn=cmd_conditions)
    sub.add_parser("geometry").set_defaults(fn=cmd_geometry)
    for name, fn in (("benchmark-cyl", cmd_benchmark_cyl), ("baseline", cmd_baseline)):
        s = sub.add_parser(name); s.set_defaults(fn=fn)
        s.add_argument("--levels", nargs="+", default=["coarse", "medium", "fine"])
        s.add_argument("--nproc", type=int, default=8)
        s.add_argument("--skip-done", action="store_true")
    s = sub.add_parser("domain-check"); s.set_defaults(fn=cmd_domain_check)
    s.add_argument("--nproc", type=int, default=8); s.add_argument("--skip-done", action="store_true")
    s = sub.add_parser("sweep"); s.set_defaults(fn=cmd_sweep)
    s.add_argument("--level", default=None); s.add_argument("--nproc", type=int, default=8)
    s.add_argument("--phase", type=int, default=None); s.add_argument("--only", nargs="*", default=None)
    s.add_argument("--skip-done", action="store_true")
    sub.add_parser("post").set_defaults(fn=cmd_post)
    s = sub.add_parser("refine"); s.set_defaults(fn=cmd_refine)
    s.add_argument("--ids", nargs="+", required=True); s.add_argument("--levels", nargs="+", default=["medium", "fine"])
    s.add_argument("--nproc", type=int, default=8); s.add_argument("--skip-done", action="store_true")
    sub.add_parser("fields").set_defaults(fn=cmd_fields)
    sub.add_parser("figures").set_defaults(fn=cmd_figures)
    sub.add_parser("uncertainty").set_defaults(fn=cmd_uncertainty)
    sub.add_parser("tables").set_defaults(fn=cmd_tables)
    sub.add_parser("versions").set_defaults(fn=cmd_versions)
    args = ap.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
