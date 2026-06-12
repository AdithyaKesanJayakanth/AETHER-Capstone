"""Structured (single-block, body-fitted) mesh generation for SU2.

Two generators:

* ``capsule_mesh``  - axisymmetric capsule family (meridional half-plane, y >= 0).
  Grid lines leave the wall along *smoothed* wall normals (wall-orthogonal in
  the boundary layer, progressively smoothed outward so lines fan around the
  shoulder and the base corner without crossing). The two end lines of the
  block are the upstream and downstream segments of the axis of symmetry,
  so the mesh is exactly consistent with the axisymmetric formulation.
* ``cylinder_mesh`` - planar half-cylinder (quarter domain with a symmetry
  line) for the Wieting Run 31 benchmark: a polar grid, exactly orthogonal.

Both write the native SU2 ASCII format (quadrilaterals, VTK type 9; line
boundary elements, VTK type 3) plus a JSON quality report, and can draw the
mesh with matplotlib. Three nested refinement levels share one definition:
the ``level`` scale factor multiplies the wall spacings and first-cell
height by 1/1.5 per level and the growth ratio is reduced accordingly.

Why structured and not Gmsh unstructured: laminar hypersonic heat flux is
set by the wall-normal temperature gradient inside a thermal layer a few
tenths of a millimetre thick; wall-orthogonal quadrilaterals with a
controlled first-cell height and growth ratio are the standard way to
resolve it, and nested refinement is exact (every spacing scales by the
same factor), which is what the Richardson/GCI analysis assumes.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from typing import Dict, Tuple

import numpy as np

from .geometry import CapsuleProfile, CapsuleParams, build_profile


# --------------------------------------------------------------------------
# 1-D distribution helpers
# --------------------------------------------------------------------------
def spacing_distribution(knots_s, knots_h, n_sub=20000) -> np.ndarray:
    """Place points on [s0, s1] so that the local spacing follows a target
    h(s) given at knots (log-linear interpolation between knots). Returns the
    point coordinates s_i (first = s0, last = s1)."""
    s = np.linspace(knots_s[0], knots_s[-1], n_sub)
    logh = np.interp(s, knots_s, np.log(knots_h))
    h = np.exp(logh)
    dN = 1.0 / h
    N = np.concatenate([[0.0], np.cumsum(0.5 * (dN[1:] + dN[:-1]) * np.diff(s))])
    n_cells = max(2, int(round(N[-1])))
    targets = np.linspace(0.0, N[-1], n_cells + 1)
    return np.interp(targets, N, s)


def geometric_series(d1: float, ratio: float, n: int) -> np.ndarray:
    k = np.arange(n + 1)
    if abs(ratio - 1.0) < 1e-12:
        return d1 * k
    return d1 * (ratio ** k - 1.0) / (ratio - 1.0)


def normal_distances(first_cell: float, ratio: float, h_cap: float,
                     d_uniform_end: float, stretch_ratio: float, n_outer: int,
                     d_far_ref: float) -> Tuple[np.ndarray, int]:
    """Wall-normal distance distribution (reference, for d_far_ref):
    geometric growth from first_cell at 'ratio' until the cell size reaches
    h_cap, then uniform cells of size h_cap until d_uniform_end, then n_outer
    geometrically stretched cells to d_far_ref. Returns (distances, index of
    the first stretched cell)."""
    d = [0.0]
    size = first_cell
    while size < h_cap:
        d.append(d[-1] + size)
        size *= ratio
    while d[-1] + h_cap < d_uniform_end:
        d.append(d[-1] + h_cap)
    i_outer = len(d) - 1
    rem = d_far_ref - d[-1]
    # stretched part: first stretched cell = h_cap, ratio chosen so that
    # n_outer cells cover 'rem'
    r = stretch_ratio
    series = geometric_series(h_cap, r, n_outer)
    # rescale (keeping ratio) if the series does not match rem: adjust ratio by bisection
    lo, hi = 1.0001, 1.6
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        tot = geometric_series(h_cap, mid, n_outer)[-1]
        if tot < rem:
            lo = mid
        else:
            hi = mid
    series = geometric_series(h_cap, 0.5 * (lo + hi), n_outer)
    d = np.array(d)
    d = np.concatenate([d, d[-1] + series[1:]])
    return d, i_outer


# --------------------------------------------------------------------------
# Capsule mesh
# --------------------------------------------------------------------------
@dataclass
class CapsuleMeshSpec:
    level: str = "medium"        # coarse / medium / fine
    # medium-level wall spacings [m]; scaled by the level factor
    h_cap: float = 0.80e-3
    h_shoulder: float = 0.30e-3
    h_cone: float = 1.10e-3
    h_corner: float = 0.20e-3
    h_base: float = 0.80e-3
    first_cell: float = 3.0e-6   # m, medium
    growth: float = 1.15         # medium
    h_normal_cap: float = 0.80e-3
    d_uniform_end_D: float = 0.45  # keep uniform normal spacing out to this many D (shock region)
    n_outer: int = 24            # stretched cells from d_uniform_end to the far boundary
    stretch_ratio: float = 1.15
    d_far_nose_D: float = 2.0    # far boundary distance at the nose, in D
    d_far_wake_D: float = 4.5    # far boundary distance behind the base, in D
    smooth_max: int = 60         # maximum normal-smoothing half-width (in wall points)
    redistribute_max: float = 0.85  # how far the far-field spacing is relaxed toward uniform
    truncate_at_base: bool = False  # forebody + cone only: outlet plane normal to the cone at its end (base and wake excluded)
    axis_offset: float = 0.0        # [m] symmetry line placed at y = axis_offset instead of y = 0 (see docs/mesh.md)

    @property
    def factor(self) -> float:
        return {"coarse": 1.5, "medium": 1.0, "fine": 1.0 / 1.5}[self.level]

    @property
    def level_growth(self) -> float:
        # growth ratio scales so that the number of cells across a fixed
        # layer thickness scales by the same factor as the spacing
        return 1.0 + (self.growth - 1.0) * self.factor


def _wall_points_and_normals(prof: CapsuleProfile, spec: CapsuleMeshSpec):
    p = prof.params
    f = spec.factor
    D = p.D
    s_knots = [0.0, 0.6 * prof.s_P1, prof.s_P1, prof.s_P2,
               prof.s_P2 + 0.25 * (prof.s_P3 - prof.s_P2),
               prof.s_P3 - 0.15 * (prof.s_P3 - prof.s_P2), prof.s_P3, prof.s_Pf,
               prof.s_Pf + 0.4 * (prof.s_P4 - prof.s_Pf), prof.s_P4]
    h_knots = [spec.h_cap, spec.h_cap, spec.h_shoulder, spec.h_shoulder,
               spec.h_cone, spec.h_cone, spec.h_corner, spec.h_corner, spec.h_base, spec.h_base]
    h_knots = [h * f for h in h_knots]
    if spec.truncate_at_base:
        s_knots = s_knots[:5] + [prof.s_P3]
        h_knots = h_knots[:5] + [spec.h_cone * f]
    s = spacing_distribution(s_knots, h_knots)
    # make sure the corner P3 and the joins are grid points (snap nearest)
    for sj in (prof.s_P1, prof.s_P2, prof.s_P3, prof.s_Pf):
        if sj <= s[-1] + 1e-15:
            k = int(np.argmin(np.abs(s - sj)))
            s[k] = sj
    s = np.unique(s)
    xy = np.zeros((len(s), 2))
    nrm = np.zeros((len(s), 2))
    Rn, Rs, Cs, th, rf, Cf = p.Rn, p.Rs, prof.center_s, p.theta_c, p.rf, prof.center_f
    for i, si in enumerate(s):
        if si <= prof.s_P1 + 1e-14:
            phi = si / Rn
            xy[i] = (Rn - Rn * math.cos(phi), Rn * math.sin(phi))
            nrm[i] = (-math.cos(phi), math.sin(phi))
        elif si <= prof.s_P2 + 1e-14:
            psi = prof.phi1 + (si - prof.s_P1) / Rs
            xy[i] = (Cs[0] - Rs * math.cos(psi), Cs[1] + Rs * math.sin(psi))
            nrm[i] = (-math.cos(psi), math.sin(psi))
        elif si <= prof.s_P3 + 1e-14:
            t = si - prof.s_P2
            xy[i] = (prof.P2[0] + t * math.cos(th), prof.P2[1] - t * math.sin(th))
            nrm[i] = (math.sin(th), math.cos(th))
        elif si <= prof.s_Pf + 1e-14:
            ang = (math.pi / 2 - th) - (si - prof.s_P3) / rf
            xy[i] = (Cf[0] + rf * math.cos(ang), Cf[1] + rf * math.sin(ang))
            nrm[i] = (math.cos(ang), math.sin(ang))
        else:
            t = si - prof.s_Pf
            xy[i] = (prof.Pf[0], prof.Pf[1] - t)
            nrm[i] = (1.0, 0.0)
    xy[0] = (0.0, 0.0); nrm[0] = (-1.0, 0.0)
    if spec.truncate_at_base:
        xy[-1] = prof.P3; nrm[-1] = (math.sin(th), math.cos(th))
    else:
        xy[-1] = (prof.P4[0], 0.0); nrm[-1] = (1.0, 0.0)
    return s, xy, nrm


def _smooth_normals(nrm: np.ndarray, half_width: int, end_fixed: bool = False) -> np.ndarray:
    """Box-filter the normal field along the wall with reflection at the
    axis end points (mirror normals: (nx, -ny)), then renormalise. With
    end_fixed the last normal is held (constant extension) so that the last
    grid line is straight along it (used for the truncated-domain outlet)."""
    if half_width <= 0:
        return nrm.copy()
    n = len(nrm)
    w = min(half_width, n - 2)
    left = nrm[1:w + 1][::-1] * np.array([1.0, -1.0])
    if end_fixed:
        right = np.tile(nrm[-1], (w, 1))
    else:
        right = nrm[-w - 1:-1][::-1] * np.array([1.0, -1.0])
    ext = np.vstack([left, nrm, right])
    kern = np.ones(2 * w + 1) / (2 * w + 1)
    sx = np.convolve(ext[:, 0], kern, mode="valid")
    sy = np.convolve(ext[:, 1], kern, mode="valid")
    out = np.column_stack([sx, sy])
    out[0, 1] = 0.0
    if end_fixed:
        out[-1] = nrm[-1]
    else:
        out[-1, 1] = 0.0
    out /= np.linalg.norm(out, axis=1)[:, None]
    return out


def _egg_boundary(prof: CapsuleProfile, spec: CapsuleMeshSpec):
    """Smooth closed far boundary: a circle of radius R_far centred on the body
    mid-length upstream of that centre, continued downstream by an ellipse
    with the same minor axis, so the whole curve is C1. Returns a function
    f(x, y) < 0 inside, > 0 outside."""
    D = prof.params.D
    xc = 0.5 * prof.length
    R_far = spec.d_far_nose_D * D + xc
    a_dn = prof.length + spec.d_far_wake_D * D - xc

    def f(x, y):
        if x <= xc:
            return (x - xc) ** 2 + y ** 2 - R_far ** 2
        return ((x - xc) / a_dn) ** 2 + (y / R_far) ** 2 - 1.0
    return f


def _ray_to_boundary(p, n, f, d_lo, d_hi):
    """Distance along the ray p + d n at which f changes sign (bisection)."""
    for _ in range(60):
        mid = 0.5 * (d_lo + d_hi)
        if f(p[0] + mid * n[0], p[1] + mid * n[1]) < 0.0:
            d_lo = mid
        else:
            d_hi = mid
    return 0.5 * (d_lo + d_hi)


def _redistribute_level(xy: np.ndarray, w: float) -> np.ndarray:
    """Move the points of one grid level along their own curve so that the
    spacing is a blend between the inherited (wall) distribution and a
    uniform arc-length distribution; end points stay fixed."""
    if w <= 0.0:
        return xy
    seg = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    f_cur = s / s[-1]
    f_uni = np.linspace(0.0, 1.0, len(s))
    f_new = (1.0 - w) * f_cur + w * f_uni
    x = np.interp(f_new * s[-1], s, xy[:, 0])
    y = np.interp(f_new * s[-1], s, xy[:, 1])
    out = np.column_stack([x, y])
    out[0] = xy[0]; out[-1] = xy[-1]
    return out


def capsule_mesh(params: CapsuleParams, spec: CapsuleMeshSpec) -> "StructuredMesh":
    prof = build_profile(params)
    D = params.D
    f = spec.factor
    s, xy, nrm = _wall_points_and_normals(prof, spec)
    ni = len(s)
    d_far_ref = spec.d_far_nose_D * D
    d, i_outer = normal_distances(spec.first_cell * f, spec.level_growth,
                                  spec.h_normal_cap * f, spec.d_uniform_end_D * D,
                                  spec.stretch_ratio, int(round(spec.n_outer / f)),
                                  d_far_ref)
    nj = len(d)
    inner_end = d[i_outer]
    # far-field direction: heavily smoothed normals; far distance from the ray/egg intersection
    egg = _egg_boundary(prof, spec)
    n_far = _smooth_normals(nrm, int(round(spec.smooth_max / f)), spec.truncate_at_base)
    d_far = np.array([_ray_to_boundary(xy[i], n_far[i], egg, inner_end, 20.0 * D) for i in range(ni)])
    # per-column distance table: inner part fixed, outer part rescaled to d_far(i)
    dist = np.tile(d, (ni, 1))
    outer_ref = d[i_outer:] - inner_end
    for i in range(ni):
        dist[i, i_outer:] = inner_end + outer_ref * (d_far[i] - inner_end) / (d_far_ref - inner_end)
    X = np.zeros((ni, nj, 2))
    cache: Dict[int, np.ndarray] = {}
    for j in range(nj):
        frac = min(1.0, d[j] / d_far_ref)
        hw = int(round(spec.smooth_max / f * math.sqrt(frac)))
        if hw not in cache:
            cache[hw] = _smooth_normals(nrm, hw, spec.truncate_at_base)
        nj_ = cache[hw]
        X[:, j, 0] = xy[:, 0] + dist[:, j] * nj_[:, 0]
        X[:, j, 1] = xy[:, 1] + dist[:, j] * nj_[:, 1]
        # relax the wall clustering with distance: uniform-ish spacing far away
        d_bl = spec.d_uniform_end_D * D * 0.25
        if d[j] > d_bl:
            t = min(1.0, (d[j] - d_bl) / (d_far_ref - d_bl))
            w = spec.redistribute_max * (t * t * (3.0 - 2.0 * t))
            X[:, j, :] = _redistribute_level(X[:, j, :], w)
    X[0, :, 1] = spec.axis_offset
    if spec.truncate_at_base:
        markers = {"wall": "j0", "axis": "i0", "outflow": "iN", "farfield": "jN"}
    else:
        X[-1, :, 1] = spec.axis_offset
        markers = {"wall": "j0", "axis": "i0+iN", "farfield": "jN"}
    X[:, :, 1] = np.maximum(X[:, :, 1], spec.axis_offset)
    mesh = StructuredMesh(X, markers=markers,
                          info={"kind": "capsule", "level": spec.level, "ni": ni, "nj": nj,
                                "truncate_at_base": spec.truncate_at_base, "axis_offset": spec.axis_offset,
                                "first_cell_m": spec.first_cell * f, "growth": spec.level_growth,
                                "d_far_nose_D": spec.d_far_nose_D, "d_far_wake_D": spec.d_far_wake_D,
                                "s_wall": s.tolist(), "params": asdict(params),
                                "shield_arc_length_m": prof.s_P2,
                                "landmarks_s": {"P1": prof.s_P1, "Pmax": prof.s_Pmax, "P2": prof.s_P2,
                                                "P3": prof.s_P3, "Pf": prof.s_Pf, "P4": prof.s_P4}})
    return mesh


# --------------------------------------------------------------------------
# Planar cylinder mesh (Wieting benchmark)
# --------------------------------------------------------------------------
@dataclass
class CylinderMeshSpec:
    level: str = "medium"
    radius: float = 0.0381
    n_theta: int = 140           # medium, over 0..theta_max
    theta_max_deg: float = 105.0 # outlet placed past the 90 deg station used for comparisons
    first_cell: float = 1.0e-6   # m, medium
    growth: float = 1.12
    h_normal_cap: float = 0.25e-3
    d_uniform_end_R: float = 0.7  # uniform normal spacing out to this many R (covers the shock at ~0.42 R)
    n_outer: int = 20
    stretch_ratio: float = 1.15
    r_far_R: float = 3.0
    axis_offset: float = 0.0     # [m] symmetry line at y = axis_offset (used only for the axisymmetric sphere test)

    @property
    def factor(self):
        return {"coarse": 1.5, "medium": 1.0, "fine": 1.0 / 1.5}[self.level]

    @property
    def level_growth(self):
        return 1.0 + (self.growth - 1.0) * self.factor


def cylinder_mesh(spec: CylinderMeshSpec) -> "StructuredMesh":
    f = spec.factor
    R = spec.radius
    ni = int(round(spec.n_theta / f)) + 1
    theta = np.linspace(0.0, math.radians(spec.theta_max_deg), ni)     # 0 = stagnation line
    d, i_outer = normal_distances(spec.first_cell * f, spec.level_growth,
                                  spec.h_normal_cap * f, spec.d_uniform_end_R * R,
                                  spec.stretch_ratio, int(round(spec.n_outer / f)),
                                  (spec.r_far_R - 1.0) * R)
    nj = len(d)
    r = R + d
    X = np.zeros((ni, nj, 2))
    X[:, :, 0] = -np.outer(np.cos(theta), r)
    X[:, :, 1] = np.outer(np.sin(theta), r)
    X[0, :, 1] = spec.axis_offset
    return StructuredMesh(X, markers={"wall": "j0", "symmetry": "i0", "outflow": "iN", "farfield": "jN"},
                          info={"kind": "cylinder", "level": spec.level, "ni": ni, "nj": nj,
                                "first_cell_m": spec.first_cell * f, "growth": spec.level_growth,
                                "radius": R, "r_far_R": spec.r_far_R,
                                "theta_deg": np.degrees(theta).tolist()})


# --------------------------------------------------------------------------
# Mesh container, quality, SU2 writer, plotting
# --------------------------------------------------------------------------
class StructuredMesh:
    def __init__(self, X: np.ndarray, markers: Dict[str, str], info: dict):
        self.X = X                      # (ni, nj, 2)
        self.markers = markers          # name -> "j0" | "jN" | "i0" | "iN" | "i0+iN"
        self.info = info
        self.ni, self.nj = X.shape[0], X.shape[1]

    # ---- quality ----------------------------------------------------------
    def quality(self) -> dict:
        X = self.X
        a = X[:-1, :-1]; b = X[1:, :-1]; c = X[1:, 1:]; d = X[:-1, 1:]
        # signed area via shoelace (counter-clockwise positive)
        area = 0.5 * ((a[..., 0] * b[..., 1] - b[..., 0] * a[..., 1]) +
                      (b[..., 0] * c[..., 1] - c[..., 0] * b[..., 1]) +
                      (c[..., 0] * d[..., 1] - d[..., 0] * c[..., 1]) +
                      (d[..., 0] * a[..., 1] - a[..., 0] * d[..., 1]))

        def ang(p, q, r):
            u = p - q; v = r - q
            cosang = np.sum(u * v, axis=-1) / (np.linalg.norm(u, axis=-1) * np.linalg.norm(v, axis=-1) + 1e-300)
            return np.degrees(np.arccos(np.clip(cosang, -1, 1)))
        angles = np.stack([ang(d, a, b), ang(a, b, c), ang(b, c, d), ang(c, d, a)])
        e1 = np.linalg.norm(b - a, axis=-1); e2 = np.linalg.norm(c - b, axis=-1)
        e3 = np.linalg.norm(d - c, axis=-1); e4 = np.linalg.norm(a - d, axis=-1)
        l_xi = 0.5 * (e1 + e3); l_eta = 0.5 * (e2 + e4)
        aspect = np.maximum(l_xi, l_eta) / (np.minimum(l_xi, l_eta) + 1e-300)
        return {
            "n_cells": int(area.size), "n_points": int(self.ni * self.nj),
            "min_area": float(area.min()), "n_negative_area": int((area <= 0).sum()),
            "min_angle_deg": float(angles.min()), "max_angle_deg": float(angles.max()),
            "max_aspect_ratio": float(aspect.max()),
            "first_cell_height_min": float(np.linalg.norm(X[:, 1] - X[:, 0], axis=-1).min()),
            "first_cell_height_max": float(np.linalg.norm(X[:, 1] - X[:, 0], axis=-1).max()),
            "ni": self.ni, "nj": self.nj,
        }

    # ---- SU2 writer ---------------------------------------------------------
    def node(self, i, j):
        return j * self.ni + i

    def write_su2(self, path: str) -> None:
        ni, nj = self.ni, self.nj
        X = self.X
        lines = ["NDIME= 2", f"NELEM= {(ni - 1) * (nj - 1)}"]
        k = 0
        for j in range(nj - 1):
            for i in range(ni - 1):
                lines.append(f"9 {self.node(i, j)} {self.node(i + 1, j)} {self.node(i + 1, j + 1)} {self.node(i, j + 1)} {k}")
                k += 1
        lines.append(f"NPOIN= {ni * nj}")
        k = 0
        for j in range(nj):
            for i in range(ni):
                lines.append(f"{X[i, j, 0]:.12e} {X[i, j, 1]:.12e} {k}")
                k += 1
        lines.append(f"NMARK= {len(self.markers)}")
        for name, where in self.markers.items():
            elems = []
            for part in where.split("+"):
                if part == "j0":
                    elems += [(self.node(i, 0), self.node(i + 1, 0)) for i in range(ni - 1)]
                elif part == "jN":
                    elems += [(self.node(i, nj - 1), self.node(i + 1, nj - 1)) for i in range(ni - 1)]
                elif part == "i0":
                    elems += [(self.node(0, j), self.node(0, j + 1)) for j in range(nj - 1)]
                elif part == "iN":
                    elems += [(self.node(ni - 1, j), self.node(ni - 1, j + 1)) for j in range(nj - 1)]
            lines.append(f"MARKER_TAG= {name}")
            lines.append(f"MARKER_ELEMS= {len(elems)}")
            lines += [f"3 {a} {b}" for a, b in elems]
        with open(path, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def write_report(self, path: str) -> dict:
        rep = {"quality": self.quality(), "markers": self.markers,
               "info": {k: v for k, v in self.info.items() if k not in ("s_wall", "theta_deg")}}
        with open(path, "w") as fh:
            json.dump(rep, fh, indent=2)
        return rep

    # ---- plotting -----------------------------------------------------------
    def plot(self, path: str, zoom: Tuple[float, float, float, float] | None = None,
             title: str = "", every: int = 1) -> None:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
        X = self.X
        segs = []
        for i in range(0, self.ni, every):
            segs.append(X[i, :, :])
        for j in range(0, self.nj, every):
            segs.append(X[:, j, :])
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.add_collection(LineCollection(segs, colors="0.25", linewidths=0.3))
        ax.plot(X[:, 0, 0], X[:, 0, 1], "r-", lw=1.0, label="wall")
        ax.set_aspect("equal")
        if zoom:
            ax.set_xlim(zoom[0], zoom[1]); ax.set_ylim(zoom[2], zoom[3])
        else:
            ax.autoscale()
        ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]")
        if title:
            ax.set_title(title)
        fig.tight_layout()
        fig.savefig(path, dpi=160)
        plt.close(fig)
