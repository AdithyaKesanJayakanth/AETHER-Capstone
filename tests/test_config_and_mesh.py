import os
import re

import numpy as np
import pytest

from aether.cases import baseline_params
from aether.mesh import capsule_mesh, CapsuleMeshSpec, cylinder_mesh, CylinderMeshSpec
from aether.su2config import CaseSettings, _render
from aether.convergence import gci


def test_config_renders_without_placeholders():
    s = CaseSettings(kind="capsule", mach=10.18, p_inf=190.5, T_inf=48.6, T_wall=300.0,
                     ref_length=0.17577, ref_area=0.024266)
    for stage in (1, 2):
        txt = _render(s, stage)
        body = "\n".join(ln for ln in txt.splitlines() if not ln.startswith("%"))
        assert not re.findall(r"\{[a-z_0-9]+\}", body)
        assert "AXISYMMETRIC= YES" in txt
        assert "MARKER_ISOTHERMAL= ( wall, 300.0000 )" in txt
    assert "MUSCL_FLOW= NO" in _render(s, 1)
    assert "MUSCL_FLOW= YES" in _render(s, 2)
    assert "RESTART_SOL= YES" in _render(s, 2)


def test_cylinder_config_is_planar():
    s = CaseSettings(kind="cylinder", mach=8.03, p_inf=855.0, T_inf=124.94, T_wall=294.44,
                     ref_length=0.0381, ref_area=0.0762)
    txt = _render(s, 1)
    assert "AXISYMMETRIC= NO" in txt
    assert "MARKER_SUPERSONIC_OUTLET= ( outflow )" in txt


def test_capsule_mesh_levels_are_nested_and_valid():
    p = baseline_params()
    counts = []
    for level in ("coarse", "medium", "fine"):
        m = capsule_mesh(p, CapsuleMeshSpec(level=level))
        q = m.quality()
        assert q["n_negative_area"] == 0
        assert q["min_angle_deg"] > 30.0
        counts.append(q["n_cells"])
        # wall nodes on the axis at both ends
        assert m.X[0, 0, 1] == 0.0 and m.X[-1, 0, 1] == 0.0
        assert np.all(m.X[:, :, 1] >= 0.0)
    # refinement ratio 1.5 per direction -> cell count ratio about 2.25
    assert 1.9 < counts[1] / counts[0] < 2.6
    assert 1.9 < counts[2] / counts[1] < 2.6


def test_capsule_mesh_first_cell_scales_with_level():
    p = baseline_params()
    h = {lvl: capsule_mesh(p, CapsuleMeshSpec(level=lvl)).quality()["first_cell_height_max"] for lvl in ("coarse", "medium", "fine")}
    assert h["coarse"] == pytest.approx(1.5 * h["medium"], rel=1e-6)
    assert h["fine"] == pytest.approx(h["medium"] / 1.5, rel=1e-6)


def test_cylinder_mesh_orthogonal():
    m = cylinder_mesh(CylinderMeshSpec(level="coarse"))
    q = m.quality()
    assert q["n_negative_area"] == 0
    assert 89.0 < q["min_angle_deg"] <= 90.0


def test_su2_writer_roundtrip(tmp_path):
    from aether.vtkio import read_su2_wall
    m = cylinder_mesh(CylinderMeshSpec(level="coarse"))
    path = tmp_path / "m.su2"
    m.write_su2(str(path))
    wall = read_su2_wall(str(path))
    assert wall.shape == (m.ni, 2)
    assert np.allclose(wall, m.X[:, 0, :])


def test_gci_recovers_second_order_sequence():
    # f(h) = f_exact + c h^2 with r = 1.5
    f_exact, c = 1.0, 0.1
    h1, h2, h3 = 1.0, 1.5, 2.25
    g = gci(f_exact + c * h1 ** 2, f_exact + c * h2 ** 2, f_exact + c * h3 ** 2, r=1.5)
    assert g["p"] == pytest.approx(2.0, rel=1e-6)
    assert g["f_extrapolated"] == pytest.approx(f_exact, rel=1e-6)
