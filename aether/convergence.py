"""Mesh-convergence assessment: Richardson extrapolation and the Grid
Convergence Index (Roache 1994; Celik et al. 2008, J. Fluids Eng. 130).

Inputs are three solutions f1 (fine), f2 (medium), f3 (coarse) on meshes
with a constant refinement ratio r (here 1.5 in each direction, so r = 1.5
for a 2-D quantity measured per unit length; we use the linear ratio).
"""
from __future__ import annotations

import math
from typing import Optional


def gci(f1: float, f2: float, f3: float, r: float = 1.5, Fs: float = 1.25) -> dict:
    """Return observed order p, Richardson-extrapolated value, relative
    errors and GCI for the fine (1) and medium (2) meshes.

    If the sequence is not monotone (oscillatory convergence) the order
    cannot be estimated; the function reports that and falls back to p = 1
    for a conservative GCI with Fs = 3 (Roache's recommendation for two-grid
    estimates)."""
    e21 = f2 - f1
    e32 = f3 - f2
    out = {"f1": f1, "f2": f2, "f3": f3, "r": r}
    if e21 == 0 or e32 == 0 or (e32 / e21) <= 0:
        out.update({"monotone": False, "p": None, "p_used": 1.0, "Fs_used": 3.0})
        p = 1.0; Fs = 3.0
    else:
        p = abs(math.log(abs(e32 / e21)) / math.log(r))
        out.update({"monotone": True, "p": p, "p_used": p, "Fs_used": Fs})
    rp = r ** p - 1.0
    f_ext = f1 + (f1 - f2) / rp if rp > 0 else f1
    out["f_extrapolated"] = f_ext
    ea21 = abs(e21 / f1) if f1 else float("nan")
    ea32 = abs(e32 / f2) if f2 else float("nan")
    out["rel_err_21"] = ea21
    out["rel_err_32"] = ea32
    out["ext_rel_err_fine"] = abs((f_ext - f1) / f_ext) if f_ext else float("nan")
    out["GCI_fine"] = Fs * ea21 / rp if rp > 0 else float("nan")
    out["GCI_medium"] = Fs * ea32 / rp if rp > 0 else float("nan")
    out["asymptotic_ratio"] = (out["GCI_medium"] / (r ** p * out["GCI_fine"])) if out["GCI_fine"] else float("nan")
    return out


def two_grid_uncertainty(f_fine: float, f_coarse: float, r: float = 1.5, p: float = 1.0, Fs: float = 3.0) -> float:
    """Conservative GCI for a quantity available on only two meshes."""
    return Fs * abs((f_coarse - f_fine) / f_fine) / (r ** p - 1.0)
