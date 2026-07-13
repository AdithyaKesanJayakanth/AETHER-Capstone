"""Trade-space analysis: nondominated set, selection rules and their sensitivity.

Objectives (both evaluated at the same free stream and reference area):
  maximise C_D            -> we minimise f1 = -C_D
  minimise q''_max,shield -> f2 = q''_max over the nose cap + shoulder

A design A dominates B if A is at least as good in both objectives and
strictly better in at least one. With numerical uncertainty u_cd and u_q
(from the mesh study, as relative values) two designs whose objectives
differ by less than the uncertainty are treated as indistinguishable: the
"robust" nondominated set keeps every design that is not dominated by a
margin larger than the uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import numpy as np
import pandas as pd


@dataclass
class SelectionRule:
    name: str
    description: str
    cd_fraction_of_baseline: float   # drag target as a fraction of the baseline C_D


DEFAULT_RULES = [
    SelectionRule("lowest_q_at_98pct_drag", "lowest peak heat flux among designs with C_D >= 0.98 C_D,baseline", 0.98),
    SelectionRule("lowest_q_at_95pct_drag", "lowest peak heat flux among designs with C_D >= 0.95 C_D,baseline", 0.95),
    SelectionRule("lowest_q_at_baseline_drag", "lowest peak heat flux among designs with C_D >= C_D,baseline", 1.00),
]


def nondominated(df: pd.DataFrame, cd_col: str = "cd", q_col: str = "q_max_shield",
                 u_cd: float = 0.0, u_q: float = 0.0) -> np.ndarray:
    """Boolean mask of nondominated rows. With u_cd/u_q > 0 (relative),
    domination requires exceeding the uncertainty margins."""
    cd = df[cd_col].to_numpy(); q = df[q_col].to_numpy()
    n = len(df)
    nd = np.ones(n, dtype=bool)
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            better_cd = cd[j] >= cd[i] * (1.0 + u_cd)
            better_q = q[j] <= q[i] * (1.0 - u_q)
            noworse_cd = cd[j] >= cd[i] * (1.0 - u_cd)
            noworse_q = q[j] <= q[i] * (1.0 + u_q)
            if (better_cd and noworse_q) or (better_q and noworse_cd):
                nd[i] = False
                break
    return nd


def select(df: pd.DataFrame, rule: SelectionRule, cd_baseline: float,
           cd_col: str = "cd", q_col: str = "q_max_shield") -> Optional[pd.Series]:
    ok = df[df[cd_col] >= rule.cd_fraction_of_baseline * cd_baseline]
    if ok.empty:
        return None
    return ok.loc[ok[q_col].idxmin()]


def analyse(results: pd.DataFrame, baseline_id: str = "B00", u_cd: float = 0.0, u_q: float = 0.0,
            rules: List[SelectionRule] = DEFAULT_RULES) -> dict:
    df = results[(results["kind"] == "capsule") & (results["status"] == "converged")].copy()
    df = df[df["case_id"].astype(str).str.len() > 0]
    # the trade space is the sweep plus the baseline at the sweep level; mesh levels and checks are excluded
    df = df[df["group"].isin(["nose", "cone", "shoulder", "combo"]) | (df["case_id"] == baseline_id)]
    base = df[df["case_id"] == baseline_id]
    if base.empty:
        raise ValueError("baseline not found among converged cases")
    cd_b = float(base["cd"].iloc[0]); q_b = float(base["q_max_shield"].iloc[0])
    df["nondominated"] = nondominated(df)
    df["nondominated_robust"] = nondominated(df, u_cd=u_cd, u_q=u_q)
    df["cd_rel_baseline"] = df["cd"] / cd_b - 1.0
    df["q_rel_baseline"] = df["q_max_shield"] / q_b - 1.0
    out = {"baseline": {"case_id": baseline_id, "cd": cd_b, "q_max_shield": q_b},
           "uncertainty": {"u_cd": u_cd, "u_q": u_q},
           "n_cases": int(len(df)),
           "nondominated": df[df["nondominated"]]["case_id"].tolist(),
           "nondominated_robust": df[df["nondominated_robust"]]["case_id"].tolist(),
           "highest_drag": df.loc[df["cd"].idxmax(), "case_id"],
           "lowest_heating": df.loc[df["q_max_shield"].idxmin(), "case_id"],
           "selections": {}}
    for r in rules:
        s = select(df, r, cd_b)
        out["selections"][r.name] = None if s is None else {
            "case_id": s["case_id"], "cd": float(s["cd"]), "q_max_shield": float(s["q_max_shield"]),
            "cd_rel_baseline": float(s["cd_rel_baseline"]), "q_rel_baseline": float(s["q_rel_baseline"]),
            "rule": r.description}
    return out, df


def sensitivities(df: pd.DataFrame, baseline_id: str = "B00") -> pd.DataFrame:
    """One-variable sensitivities: relative change of C_D and q_max per
    unit change of each parameter, from the one-at-a-time cases."""
    base = df[df["case_id"] == baseline_id].iloc[0]
    rows = []
    for _, r in df.iterrows():
        if r["case_id"] == baseline_id:
            continue
        changed = [p for p in ("Rn_D", "Rs_D", "theta_c_deg") if abs(r[p] - base[p]) > 1e-4]
        if len(changed) != 1:
            continue
        p = changed[0]
        dp = r[p] - base[p]
        rows.append({"case_id": r["case_id"], "parameter": p, "delta": dp,
                     "dCD_rel": r["cd"] / base["cd"] - 1.0, "dq_rel": r["q_max_shield"] / base["q_max_shield"] - 1.0,
                     "dCD_rel_per_unit": (r["cd"] / base["cd"] - 1.0) / dp,
                     "dq_rel_per_unit": (r["q_max_shield"] / base["q_max_shield"] - 1.0) / dp})
    return pd.DataFrame(rows)
