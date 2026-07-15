"""SU2 binary restart files: read, write and interpolate a converged solution
onto another mesh (solution-sequenced initialisation).

Format (SU2 v7/v8 CSU2BinaryFileWriter): five int32 (535532, nFields, nPoints,
0, 0), nFields names of 33 bytes each, then nPoints x nFields float64 in mesh
point order. The fields written by this study's configuration are
x, y, Density, Momentum_x, Momentum_y, Energy.

A stage-2 run initialised from a neighbouring converged solution starts on
that solution's branch; the physical-branch check still decides whether the
converged state is accepted. The interpolation is linear on the Delaunay
triangulation of the source points, with nearest-point values outside the
source hull (points behind the wall of a different shape).
"""
from __future__ import annotations

import struct
from typing import List, Tuple

import numpy as np

MAGIC = 535532
NAME_LEN = 33


def read_restart(path: str) -> Tuple[List[str], np.ndarray]:
    with open(path, "rb") as fh:
        magic, nf, npt, _, _ = struct.unpack("5i", fh.read(20))
        if magic != MAGIC:
            raise ValueError(f"{path}: not an SU2 binary restart (magic {magic})")
        names = [fh.read(NAME_LEN).split(b"\0")[0].decode() for _ in range(nf)]
        data = np.frombuffer(fh.read(8 * nf * npt), dtype=np.float64).reshape(npt, nf).copy()
    return names, data


def write_restart(path: str, names: List[str], data: np.ndarray) -> None:
    data = np.ascontiguousarray(data, dtype=np.float64)
    npt, nf = data.shape
    assert nf == len(names)
    with open(path, "wb") as fh:
        fh.write(struct.pack("5i", MAGIC, nf, npt, 0, 0))
        for n in names:
            fh.write(n.encode().ljust(NAME_LEN, b"\0")[:NAME_LEN])
        fh.write(data.tobytes())


def read_su2_points(mesh_path: str) -> np.ndarray:
    with open(mesh_path) as fh:
        for ln in fh:
            if ln.startswith("NPOIN="):
                n = int(ln.split("=")[1])
                return np.array([[float(v) for v in next(fh).split()[:2]] for _ in range(n)])
    raise ValueError(f"NPOIN not found in {mesh_path}")


def interpolate_restart(src_restart: str, dst_mesh: str, dst_restart: str) -> dict:
    """Interpolate the solution of src_restart onto the points of dst_mesh and
    write dst_restart. Returns a small record for the case summary."""
    from scipy.interpolate import LinearNDInterpolator, NearestNDInterpolator
    names, data = read_restart(src_restart)
    ix, iy = names.index("x"), names.index("y")
    src_xy = data[:, [ix, iy]]
    sol_cols = [i for i, n in enumerate(names) if n not in ("x", "y")]
    pts = read_su2_points(dst_mesh)
    lin = LinearNDInterpolator(src_xy, data[:, sol_cols])
    near = NearestNDInterpolator(src_xy, data[:, sol_cols])
    vals = lin(pts)
    outside = np.isnan(vals[:, 0])
    if outside.any():
        vals[outside] = near(pts[outside])
    out = np.zeros((len(pts), len(names)))
    out[:, ix] = pts[:, 0]; out[:, iy] = pts[:, 1]
    out[:, sol_cols] = vals
    write_restart(dst_restart, names, out)
    return {"source": src_restart, "n_source": int(len(src_xy)), "n_target": int(len(pts)),
            "n_outside_hull": int(outside.sum())}
