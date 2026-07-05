import math

import numpy as np
import pytest

from aether.geometry import (CapsuleParams, InvalidGeometry, apollo_045_scale,
                             build_profile, check_profile, sample_profile,
                             arc_length, tangent_discontinuity_deg)


def test_apollo_baseline_matches_tm_x1243_landmarks():
    """TM X-1243 states the cap/toroid tangency at S/R = 0.965 and the
    maximum body radius at S/R = 1.08 for the clean Apollo configuration."""
    p = apollo_045_scale()
    prof = build_profile(p)
    assert prof.s_P1 / p.R == pytest.approx(0.965, abs=0.003)
    assert prof.s_Pmax / p.R == pytest.approx(1.08, abs=0.005)
    assert prof.Pmax[1] == pytest.approx(p.R, rel=1e-12)
    assert check_profile(prof) == []


def test_joins_are_tangent():
    for Rn in (0.6, 1.0, 1.202, 1.6):
        for Rs in (0.03, 0.0506, 0.12):
            for th in (25.0, 33.0, 41.0):
                prof = build_profile(CapsuleParams(0.1758, Rn, Rs, th))
                xy = sample_profile(prof, 400, 200, 100, 10)
                interior = xy[xy[:, 0] < prof.P3[0] - 1e-12]
                # the maximum turning angle between consecutive samples must be
                # that of the finest arc discretisation, not a kink
                assert tangent_discontinuity_deg(interior) < 1.0
                assert check_profile(prof) == []


def test_closure_rule_derives_length_from_angle():
    base = CapsuleParams(0.1758, 1.202, 0.0506, 33.0)
    steeper = CapsuleParams(0.1758, 1.202, 0.0506, 41.0)
    assert build_profile(steeper).length < build_profile(base).length


def test_volume_increases_with_shallower_cone():
    v33 = build_profile(CapsuleParams(0.1758, 1.202, 0.0506, 33.0)).volume
    v25 = build_profile(CapsuleParams(0.1758, 1.202, 0.0506, 25.0)).volume
    assert v25 > v33


def test_volume_against_analytic_cylinder_limit():
    # A very large nose radius and tiny shoulder with a steep cone approaches
    # a flat disc + cone; check volume is positive and bounded by the
    # enclosing cylinder.
    p = CapsuleParams(0.1758, 1.202, 0.0506, 33.0)
    prof = build_profile(p)
    assert 0 < prof.volume < math.pi * p.R ** 2 * prof.length


def test_invalid_shapes_rejected():
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 0.40, 0.0506, 33.0))   # nose radius < D/2
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 1.0, 1.2, 33.0))       # shoulder > nose
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 1.0, 0.05, 0.0))       # zero cone angle
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 1.0, 0.05, 33.0, rb_D=0.6))  # closure > D/2
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 1.0, 0.45, 33.0, rb_D=0.45))  # join below closure
    with pytest.raises(InvalidGeometry):
        build_profile(CapsuleParams(0.1758, 1.0, 0.05, 33.0, rb_D=0.40, rf_D=0.5))  # fillet does not fit


def test_arc_length_consistent_with_landmarks():
    p = apollo_045_scale()
    prof = build_profile(p)
    xy = sample_profile(prof, 2000, 1000, 500, 50)
    s = arc_length(xy)
    assert s[-1] == pytest.approx(prof.s_P4, rel=1e-4)
