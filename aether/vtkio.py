"""Read SU2 ParaView (.vtu) output with VTK and extract wall and axis data.

SU2's SURFACE_CSV output carries only the conservative variables, so the
primitive wall quantities (pressure, temperature, heat flux, skin friction)
are taken from the volume file by matching the mesh's wall nodes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def read_vtu(path: str) -> pd.DataFrame:
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    r = vtk.vtkXMLUnstructuredGridReader()
    r.SetFileName(path)
    r.Update()
    d = r.GetOutput()
    pts = vtk_to_numpy(d.GetPoints().GetData())
    cols = {"x": pts[:, 0], "y": pts[:, 1]}
    pd_ = d.GetPointData()
    for i in range(pd_.GetNumberOfArrays()):
        name = pd_.GetArrayName(i)
        a = vtk_to_numpy(pd_.GetArray(i))
        if a.ndim == 1:
            cols[name] = a
        else:
            for k, suf in enumerate("xyz"[: a.shape[1]]):
                cols[f"{name}_{suf}"] = a[:, k]
    return pd.DataFrame(cols)


def wall_data(vol: pd.DataFrame, wall_xy: np.ndarray, tol: float = 1e-9) -> pd.DataFrame:
    """Rows of `vol` at the wall nodes, in the order of wall_xy (nose -> base)."""
    from scipy.spatial import cKDTree
    tree = cKDTree(vol[["x", "y"]].to_numpy())
    dist, idx = tree.query(wall_xy, k=1)
    if dist.max() > max(tol, 1e-6 * np.ptp(wall_xy[:, 0])):
        raise ValueError(f"wall node mismatch: max distance {dist.max():.3e}")
    out = vol.iloc[idx].reset_index(drop=True)
    s = np.concatenate([[0.0], np.cumsum(np.hypot(np.diff(wall_xy[:, 0]), np.diff(wall_xy[:, 1])))])
    out.insert(0, "s", s)
    return out


def axis_data(vol: pd.DataFrame, x_max: float = 0.0) -> pd.DataFrame:
    on = (np.abs(vol["y"]) < 1e-12) & (vol["x"] < x_max - 1e-12)
    return vol[on].sort_values("x").reset_index(drop=True)


def read_su2_wall(mesh_path: str, marker: str = "wall") -> np.ndarray:
    """Wall node coordinates, ordered along the marker's line elements."""
    with open(mesh_path) as fh:
        lines = fh.read().splitlines()
    i = 0
    pts = None
    marker_nodes = None
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("NPOIN="):
            n = int(ln.split("=")[1])
            pts = np.array([[float(v) for v in lines[i + 1 + k].split()[:2]] for k in range(n)])
            i += n + 1
            continue
        if ln.startswith("MARKER_TAG=") and ln.split("=")[1].strip() == marker:
            ne = int(lines[i + 1].split("=")[1])
            elems = [tuple(int(v) for v in lines[i + 2 + k].split()[1:3]) for k in range(ne)]
            order = [elems[0][0]] + [e[1] for e in elems]
            marker_nodes = order
            i += ne + 2
            continue
        i += 1
    if pts is None or marker_nodes is None:
        raise ValueError(f"marker {marker} or points not found in {mesh_path}")
    return pts[marker_nodes]
