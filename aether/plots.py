"""All line/scatter figures of the project (matplotlib). Field plots are made
with ParaView (scripts/paraview_fields.py)."""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .cases import ROOT, load_conditions
from .conditions import pitot_pressure_ratio

REF = os.path.join(ROOT, "data", "reference")
FIG = os.path.join(ROOT, "results", "figures")

plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 130,
                     "savefig.dpi": 200, "axes.spines.top": False, "axes.spines.right": False})
COLORS = {"coarse": "#9ecae1", "medium": "#3182bd", "fine": "#08519c", "ref": "#d62728", "theory": "#666666"}


def _save(fig, name):
    os.makedirs(FIG, exist_ok=True)
    path = os.path.join(FIG, name)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    return path


def _wall(case_dir):
    return pd.read_csv(os.path.join(case_dir, "wall_profile.csv"))


# ---------------------------------------------------------------- benchmark A
def cylinder_validation(case_dirs: dict, name="validation_cylinder.png"):
    cond = load_conditions()["cylinder"]
    p_ref = pd.read_csv(os.path.join(REF, "wieting_run31_pressure.csv"), comment="#")
    q_ref = pd.read_csv(os.path.join(REF, "wieting_run31_heatflux.csv"), comment="#")
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for level, d in case_dirs.items():
        w = _wall(d)
        th = w["theta_deg"].to_numpy()
        axs[0].plot(th, w["Pressure"] / cond["P0"], color=COLORS[level], label=f"SU2 {level}")
        axs[1].plot(th, w["Heat_Flux"] / cond["Q0"], color=COLORS[level], label=f"SU2 {level}")
    axs[0].plot(np.abs(p_ref["theta_deg"]), p_ref["p_over_P0"], "o", color=COLORS["ref"], mfc="none", label="Wieting Run 31")
    axs[1].plot(np.abs(q_ref["theta_deg"]), q_ref["q_over_Q0"], "o", color=COLORS["ref"], mfc="none", label="Wieting Run 31")
    axs[0].set_xlabel(r"$\theta$ [deg]"); axs[0].set_ylabel(r"$p / P_0$"); axs[0].set_xlim(0, 90)
    axs[1].set_xlabel(r"$\theta$ [deg]"); axs[1].set_ylabel(r"$q'' / Q_0$"); axs[1].set_xlim(0, 90)
    axs[0].set_title("Surface pressure, M = 8.03 cylinder"); axs[1].set_title("Wall heat flux, M = 8.03 cylinder")
    axs[0].legend(); axs[1].legend()
    return _save(fig, name)


# ---------------------------------------------------------------- benchmark B
def apollo_validation(case_dirs: dict, name="validation_apollo.png"):
    p_ref = pd.read_csv(os.path.join(REF, "bertin_tmx1243_fig3a_pressure.csv"), comment="#")
    q_ref = pd.read_csv(os.path.join(REF, "bertin_tmx1243_fig8a_heating.csv"), comment="#")
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for level, d in case_dirs.items():
        with open(os.path.join(d, "case.json")) as fh:
            meta = json.load(fh)
        R = 0.5 * meta["params"]["D"]; p_t = meta["freestream"]["p_t2"]
        w = _wall(d); SR = w["s"] / R
        q = w["Heat_Flux"].to_numpy()
        q_t = q[0]          # computed stagnation-point heating (the report normalises by its measured value)
        axs[0].plot(SR, w["Pressure"] / p_t, color=COLORS[level], label=f"SU2 {level}")
        axs[1].plot(SR, q / q_t, color=COLORS[level], label=f"SU2 {level}")
    SRm = np.linspace(0, 0.965, 200)
    # modified Newtonian on the spherical cap: p/p_t = cos^2(theta) + (p_inf/p_t) sin^2(theta), theta = S/R_n
    cond = load_conditions()["main"]
    Rn_R = (8.32 / 6.92) * 2.0
    th = SRm / Rn_R
    M = cond["mach"]; pinf_pt = 1.0 / pitot_pressure_ratio(M)
    axs[0].plot(SRm, np.cos(th) ** 2 + pinf_pt * np.sin(th) ** 2, "--", color=COLORS["theory"], label="modified Newtonian")
    axs[0].plot(np.abs(p_ref["S_over_R"]), p_ref["p_over_pt"], "o", color=COLORS["ref"], mfc="none", label="TM X-1243 Fig. 3a")
    axs[1].errorbar(np.abs(q_ref["S_over_R"]), 0.5 * (q_ref["q_over_qt_min"] + q_ref["q_over_qt_max"]),
                    yerr=0.5 * (q_ref["q_over_qt_max"] - q_ref["q_over_qt_min"]), fmt="o", color=COLORS["ref"], mfc="none",
                    label="TM X-1243 Fig. 8a (range)")
    for ax in axs:
        ax.axvline(0.965, color="k", lw=0.6, ls=":"); ax.axvline(1.08, color="k", lw=0.6, ls=":")
        ax.set_xlim(0, 1.3); ax.set_xlabel("S/R")
    axs[0].set_ylabel(r"$p / p_{t2}$"); axs[1].set_ylabel(r"$q'' / q''_{t}$"); axs[1].set_ylim(0, 1.6)
    axs[0].set_title("Forebody pressure, Apollo, M = 10.18"); axs[1].set_title("Forebody heating, Apollo, M = 10.18")
    axs[0].legend(fontsize=8); axs[1].legend(fontsize=8)
    return _save(fig, name)


# ---------------------------------------------------------------- mesh study
def mesh_study(results: pd.DataFrame, case_prefix: str, name="mesh_study.png"):
    df = results[(results["case_id"].astype(str).str.startswith(case_prefix)) & (results["kind"] == "capsule")]
    df = df.sort_values("n_cells")
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.6))
    h = 1.0 / np.sqrt(df["n_cells"].to_numpy())
    axs[0].plot(h, df["cd"], "o-", color=COLORS["medium"]); axs[0].set_ylabel(r"$C_D$")
    axs[1].plot(h, df["q_max_shield"] / 1e3, "o-", color=COLORS["medium"]); axs[1].set_ylabel(r"$q''_{max}$ shield [kW/m$^2$]")
    for ax, lv in zip(axs, (df["level"], df["level"])):
        for xi, yi, lab in zip(h, (df["cd"] if ax is axs[0] else df["q_max_shield"] / 1e3), lv):
            ax.annotate(lab, (xi, yi), textcoords="offset points", xytext=(4, 4), fontsize=8)
        ax.set_xlabel(r"$h \propto 1/\sqrt{N_{cells}}$"); ax.set_xlim(0, None)
    return _save(fig, name)


# ---------------------------------------------------------------- trade space
def pareto_plot(df: pd.DataFrame, analysis: dict, name="pareto.png", u_cd=0.0, u_q=0.0):
    fig, ax = plt.subplots(figsize=(7, 5))
    groups = {"nose": ("#1f77b4", "nose radius sweep"), "cone": ("#2ca02c", "cone angle sweep"),
              "shoulder": ("#ff7f0e", "shoulder radius sweep"), "combo": ("#9467bd", "combinations"), "": ("#333333", "baseline")}
    for g, (c, lab) in groups.items():
        sub = df[df["group"].fillna("") == g]
        if sub.empty:
            continue
        ax.errorbar(sub["cd"], sub["q_max_shield"] / 1e3, xerr=u_cd * sub["cd"], yerr=u_q * sub["q_max_shield"] / 1e3,
                    fmt="o", color=c, label=lab, capsize=2, ms=6 if g else 9, mfc=c if g else "k")
        for _, r in sub.iterrows():
            ax.annotate(r["case_id"], (r["cd"], r["q_max_shield"] / 1e3), textcoords="offset points", xytext=(5, 3), fontsize=8)
    nd = df[df["nondominated"]].sort_values("cd")
    ax.plot(nd["cd"], nd["q_max_shield"] / 1e3, "-", color="#d62728", lw=1.2, label="nondominated set")
    for name_, sel in analysis["selections"].items():
        if sel and name_ == "lowest_q_at_98pct_drag":
            ax.plot(sel["cd"], sel["q_max_shield"] / 1e3, "*", color="#d62728", ms=16, mfc="none", label="selected compromise (98 % drag rule)")
    ax.set_xlabel(r"$C_D$ (whole body, $A_{ref}=\pi D^2/4$)  $\rightarrow$ better")
    ax.set_ylabel(r"$q''_{max}$ on shield [kW/m$^2$]  $\leftarrow$ better")
    ax.set_title("Drag-heating trade space, M = 10.18, Re_D = 1.1e6")
    ax.legend(fontsize=8, loc="best")
    return _save(fig, name)


def sensitivity_plot(sens: pd.DataFrame, name="sensitivities.png"):
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.6))
    for ax, p, lab in zip(axs, ("Rn_D", "theta_c_deg", "Rs_D"), (r"$R_n/D$", r"$\theta_c$ [deg]", r"$R_s/D$")):
        sub = sens[sens["parameter"] == p].sort_values("delta")
        if sub.empty:
            continue
        ax.plot(sub["delta"], 100 * sub["dCD_rel"], "o-", label=r"$\Delta C_D$ [%]")
        ax.plot(sub["delta"], 100 * sub["dq_rel"], "s-", label=r"$\Delta q''_{max}$ [%]")
        ax.axhline(0, color="k", lw=0.6); ax.set_xlabel(f"change in {lab} from baseline"); ax.legend(fontsize=8)
    axs[0].set_ylabel("change from baseline [%]")
    return _save(fig, name)


def wall_distributions(case_dirs: dict, name="wall_distributions.png"):
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for label, d in case_dirs.items():
        with open(os.path.join(d, "case.json")) as fh:
            meta = json.load(fh)
        w = _wall(d); D = meta["params"]["D"]
        axs[0].plot(w["s"] / D, w["Pressure"] / 1e3, label=label)
        axs[1].plot(w["s"] / D, w["Heat_Flux"] / 1e3, label=label)
        s2 = meta["geometry"]["s_P2"] / D
        for ax in axs:
            ax.axvline(s2, color="k", lw=0.5, ls=":")
    axs[0].set_xlabel("s/D"); axs[0].set_ylabel("wall pressure [kPa]")
    axs[1].set_xlabel("s/D"); axs[1].set_ylabel(r"wall heat flux [kW/m$^2$]")
    axs[0].legend(fontsize=8); axs[1].legend(fontsize=8)
    return _save(fig, name)


def convergence_history(case_dir: str, name: str):
    stage = 2 if os.path.exists(os.path.join(case_dir, "history_stage2.csv")) else 1
    h = pd.read_csv(os.path.join(case_dir, f"history_stage{stage}.csv")); h.columns = [c.strip().strip('"') for c in h.columns]
    fig, axs = plt.subplots(1, 3, figsize=(11, 3.3))
    axs[0].plot(h["Inner_Iter"], h["rms[Rho]"]); axs[0].set_ylabel("log10 RMS(rho residual)")
    axs[1].plot(h["Inner_Iter"], h["CD"]); axs[1].set_ylabel(r"$C_D$")
    axs[2].plot(h["Inner_Iter"], h["Avg CFL"]); axs[2].set_ylabel("average CFL")
    for ax in axs:
        ax.set_xlabel(f"iteration (stage {stage})")
    return _save(fig, name)
