"""Comparison of computed wall distributions with the reference data in
data/reference (Benchmark A: Wieting Run 31 cylinder; Benchmark B: Bertin
TM X-1243 Apollo at alpha = 0) and with the classical estimates.
"""
from __future__ import annotations

import json
import math
import os

import numpy as np
import pandas as pd

from .cases import ROOT, load_conditions, main_freestream
from .conditions import fay_riddell_stagnation, pitot_pressure_ratio

REF = os.path.join(ROOT, "data", "reference")


def _read_ref(name: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(REF, name), comment="#")


def cylinder_comparison(case_dir: str) -> dict:
    """Normalised pressure and heat flux vs theta against Wieting Run 31."""
    cond = load_conditions()["cylinder"]
    w = pd.read_csv(os.path.join(case_dir, "wall_profile.csv"))
    th = w["theta_deg"].to_numpy(); p = w["Pressure"].to_numpy(); q = w["Heat_Flux"].to_numpy()
    p_ref = _read_ref("wieting_run31_pressure.csv"); q_ref = _read_ref("wieting_run31_heatflux.csv")
    out = {"q_stag_W_m2": float(q[0]), "p_stag_Pa": float(p[0]),
           "Q0_report_W_m2": cond["Q0"], "P0_report_Pa": cond["P0"],
           "q_stag_over_Q0": float(q[0] / cond["Q0"]), "p_stag_over_P0": float(p[0] / cond["P0"]),
           "p_stag_over_rayleigh_pitot": float(p[0] / (cond["p_inf"] * pitot_pressure_ratio(cond["mach"])))}
    # Fay-Riddell (2-D) for the cylinder
    from .cases import cylinder_freestream
    fs = cylinder_freestream()
    out["fay_riddell_2d_W_m2"] = fay_riddell_stagnation(fs, cond["radius"], axisymmetric=False)
    out["q_stag_over_fay_riddell"] = float(q[0] / out["fay_riddell_2d_W_m2"])
    # distribution comparison on |theta| (model is symmetric): interpolate CFD at the data stations
    def interp(th_data, cfd_x, cfd_y):
        return np.interp(np.abs(th_data), cfd_x, cfd_y)
    q_cfd = interp(q_ref["theta_deg"].to_numpy(), th, q / q[0])
    p_cfd = interp(p_ref["theta_deg"].to_numpy(), th, p / p[0])
    q_err = q_cfd - q_ref["q_over_Q0"].to_numpy()
    p_err = p_cfd - p_ref["p_over_P0"].to_numpy()
    out["q_shape_rms_diff"] = float(np.sqrt(np.mean(q_err ** 2)))
    out["q_shape_max_abs_diff"] = float(np.max(np.abs(q_err)))
    out["p_shape_rms_diff"] = float(np.sqrt(np.mean(p_err ** 2)))
    out["p_shape_max_abs_diff"] = float(np.max(np.abs(p_err)))
    out["n_q_points"] = int(len(q_ref)); out["n_p_points"] = int(len(p_ref))
    with open(os.path.join(case_dir, "benchmark_cylinder.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return out


def apollo_comparison(case_dir: str) -> dict:
    """p/p_t and q/q_t vs S/R against TM X-1243 Figs. 3a and 8a."""
    with open(os.path.join(case_dir, "case.json")) as fh:
        meta = json.load(fh)
    fs = meta["freestream"]
    R = 0.5 * meta["params"]["D"]
    w = pd.read_csv(os.path.join(case_dir, "wall_profile.csv"))
    s = w["s"].to_numpy(); p = w["Pressure"].to_numpy(); q = w["Heat_Flux"].to_numpy()
    SR = s / R
    p_t = fs["p_t2"]
    p_ref = _read_ref("bertin_tmx1243_fig3a_pressure.csv"); q_ref = _read_ref("bertin_tmx1243_fig8a_heating.csv")
    # both sides of the pitch plane are the same meridian at alpha = 0
    pr = np.abs(p_ref["S_over_R"].to_numpy()); qr = np.abs(q_ref["S_over_R"].to_numpy())
    p_cfd = np.interp(pr, SR, p / p_t)
    q_t = float(np.median(q[(SR >= 0.1) & (SR <= 0.5)]))      # stagnation-region plateau (A.5)
    q_cfd = np.interp(qr, SR, q / q_t)
    q_mid = 0.5 * (q_ref["q_over_qt_min"] + q_ref["q_over_qt_max"]).to_numpy()
    q_half = 0.5 * (q_ref["q_over_qt_max"] - q_ref["q_over_qt_min"]).to_numpy()
    inside = np.abs(q_cfd - q_mid) <= q_half + 0.02
    out = {"p_stag_over_pt2": float(p[0] / p_t), "q_stag_W_m2": float(q[0]), "q_plateau_W_m2": q_t,
           "fay_riddell_W_m2": fay_riddell_stagnation(main_freestream(), meta["params"]["Rn_D"] * meta["params"]["D"]),
           "p_rms_diff": float(np.sqrt(np.mean((p_cfd - p_ref["p_over_pt"].to_numpy()) ** 2))),
           "p_max_abs_diff": float(np.max(np.abs(p_cfd - p_ref["p_over_pt"].to_numpy()))),
           "q_rms_diff_to_midrange": float(np.sqrt(np.mean((q_cfd - q_mid) ** 2))),
           "q_points_within_data_range": int(inside.sum()), "q_points_total": int(len(q_mid)),
           "stations": [{"S_over_R": float(a), "p_ref": float(b), "p_cfd": float(c)} for a, b, c in zip(pr, p_ref["p_over_pt"], p_cfd)],
           "q_stations": [{"S_over_R": float(a), "q_ref_min": float(b), "q_ref_max": float(c), "q_cfd": float(d)}
                          for a, b, c, d in zip(qr, q_ref["q_over_qt_min"], q_ref["q_over_qt_max"], q_cfd)]}
    out["q_plateau_over_fay_riddell"] = out["q_plateau_W_m2"] / out["fay_riddell_W_m2"]
    # forebody pressure drag from the measured distribution (modified Newtonian fairing between stations is
    # not needed: integrate the digitised points directly on the actual profile)
    with open(os.path.join(case_dir, "benchmark_apollo.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return out


def modified_newtonian_cd(case_dir: str) -> float:
    """Forebody pressure-drag coefficient from modified Newtonian theory on the
    actual profile (nose cap + shoulder up to the maximum radius)."""
    with open(os.path.join(case_dir, "case.json")) as fh:
        meta = json.load(fh)
    prof = pd.read_csv(os.path.join(case_dir, "profile.csv"), comment="#")
    x, y = prof["x"].to_numpy(), prof["y"].to_numpy()
    R = 0.5 * meta["params"]["D"]
    k = int(np.argmax(y))
    x, y = x[: k + 1], y[: k + 1]
    dx, dy = np.gradient(x), np.gradient(y)
    ds = np.hypot(dx, dy)
    nx = dy / ds   # outward normal x-component (nose faces -x)
    cp_max = 2.0 / (1.4 * meta["freestream"]["mach"] ** 2) * (pitot_pressure_ratio(meta["freestream"]["mach"]) - 1.0)
    cp = cp_max * nx ** 2        # cos^2 theta with theta the angle between normal and free stream
    # nx = dy/ds points into the body for the nose-to-shoulder traversal; the x-force on the body is +int cp nx y ds
    fx = 2.0 * math.pi * np.trapezoid(cp * nx * y, np.cumsum(ds) - ds[0])
    return float(fx / (math.pi * R * R))
