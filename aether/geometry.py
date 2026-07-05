"""Parametric axisymmetric capsule family (meridional profile).

Coordinate system: x along the axis of symmetry, positive aft (flow travels
in +x); y is the radial coordinate (y >= 0). The nose stagnation point is at
the origin. The profile is built from four analytic segments joined with
tangent (G1) continuity:

  1. spherical nose cap, radius R_n, centre (R_n, 0)
  2. toroidal shoulder, radius R_s, tangent to the cap and to the cone;
     its outermost point defines the maximum radius D/2
  3. straight rear-body cone at half-angle theta_c measured from the axis
  4. corner fillet of fixed radius r_f joining the cone to the base
  5. flat base disk of fixed radius r_b closing the body

Design variables: R_n/D, R_s/D, theta_c. Fixed: D, r_b/D, r_f/D. The aft
length is derived from the closure rule, never prescribed. The fillet is part
of the fixed closure: a sharp cone/base corner expands the hypersonic flow to
a near-vacuum state (pressure ~ 1e-3 p_inf, temperature < 1 K in test runs),
outside the perfect-gas model and numerically fragile; a small fillet bounds
the expansion the way a real machined corner does.

Derivation of the joins (see docs/geometry.md for the labelled sketch):

  cap-shoulder tangency angle phi_1 from   sin(phi_1) = (D/2 - R_s) / (R_n - R_s)
  shoulder centre                          C_s = (R_n - (R_n - R_s) cos phi_1, (R_n - R_s) sin phi_1)
  shoulder-cone tangency                   P_2 = C_s + R_s (sin theta_c, cos theta_c)
  sharp-corner position (virtual)          x_b = x_2 + (y_2 - r_b) / tan theta_c
  fillet centre                            C_f = (x_b - r_f, y_f), with n_c . (C_f - P_2) = -r_f
  fillet/cone tangency                     P_3 = C_f + r_f n_c,   n_c = (sin theta_c, cos theta_c)
  fillet/base tangency                     P_f = (x_b, y_f)
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict, field
from typing import List, Tuple

import numpy as np


class InvalidGeometry(ValueError):
    """Raised when a parameter set does not produce a valid closed profile."""


@dataclass(frozen=True)
class CapsuleParams:
    D: float                 # maximum diameter [m]
    Rn_D: float              # nose radius / D
    Rs_D: float              # shoulder radius / D
    theta_c_deg: float       # rear-body cone half-angle from the axis [deg]
    rb_D: float = 0.20       # fixed rear closure radius / D
    rf_D: float = 0.03       # fixed cone/base corner fillet radius / D

    @property
    def R(self):
        return 0.5 * self.D

    @property
    def Rn(self):
        return self.Rn_D * self.D

    @property
    def Rs(self):
        return self.Rs_D * self.D

    @property
    def rb(self):
        return self.rb_D * self.D

    @property
    def rf(self):
        return self.rf_D * self.D

    @property
    def theta_c(self):
        return math.radians(self.theta_c_deg)

    def label(self) -> str:
        return f"Rn{self.Rn_D:.3f}_Rs{self.Rs_D:.4f}_th{self.theta_c_deg:.1f}"


@dataclass
class Segment:
    kind: str                       # "arc" or "line"
    start: Tuple[float, float]
    end: Tuple[float, float]
    center: Tuple[float, float] = (0.0, 0.0)   # arcs only
    radius: float = 0.0                         # arcs only
    name: str = ""


@dataclass
class CapsuleProfile:
    params: CapsuleParams
    phi1: float                    # cap-shoulder tangency angle [rad]
    center_s: Tuple[float, float]  # shoulder torus centre
    P1: Tuple[float, float]        # cap/shoulder join
    Pmax: Tuple[float, float]      # maximum radius point
    P2: Tuple[float, float]        # shoulder/cone join
    P3: Tuple[float, float]        # cone/fillet join
    Pf: Tuple[float, float]        # fillet/base join
    P4: Tuple[float, float]        # base on axis
    center_f: Tuple[float, float]  # fillet centre
    s_P1: float                    # arc length from nose to P1
    s_Pmax: float
    s_P2: float
    s_P3: float
    s_Pf: float
    s_P4: float
    length: float                  # total length (x of base)
    volume: float                  # enclosed volume [m^3]
    wetted_area: float             # total wetted area [m^2]
    segments: List[Segment] = field(default_factory=list)

    @property
    def shield_arc_length(self) -> float:
        """Arc length of the 'heat shield' surface used for the peak heat
        flux objective: nose cap + shoulder, i.e. up to the shoulder/cone
        tangency P2."""
        return self.s_P2

    def to_dict(self) -> dict:
        d = asdict(self)
        d["params"] = asdict(self.params)
        d["segments"] = [asdict(s) for s in self.segments]
        return d


def build_profile(p: CapsuleParams) -> CapsuleProfile:
    D, R, Rn, Rs, rb, rf, th = p.D, p.R, p.Rn, p.Rs, p.rb, p.rf, p.theta_c
    if D <= 0 or Rn <= 0 or Rs <= 0 or rf <= 0:
        raise InvalidGeometry("dimensions must be positive")
    if not (0.0 < th < math.pi / 2):
        raise InvalidGeometry("cone half-angle must lie strictly between 0 and 90 deg")
    if Rs >= Rn:
        raise InvalidGeometry(f"shoulder radius {Rs:.4g} must be smaller than nose radius {Rn:.4g}")
    if Rs >= R:
        raise InvalidGeometry(f"shoulder radius {Rs:.4g} must be smaller than max radius {R:.4g}")
    if rb <= 0 or rb >= R:
        raise InvalidGeometry("closure radius must lie strictly between 0 and D/2")

    sin_phi1 = (R - Rs) / (Rn - Rs)
    if sin_phi1 > 1.0:
        raise InvalidGeometry(
            f"shoulder does not fit: (R - Rs)/(Rn - Rs) = {sin_phi1:.4f} > 1 "
            "(nose radius too small for this shoulder radius)")
    phi1 = math.asin(sin_phi1)
    # cap: centre (Rn, 0); point at angle phi from the -x direction
    P1 = (Rn - Rn * math.cos(phi1), Rn * math.sin(phi1))
    Cs = (Rn - (Rn - Rs) * math.cos(phi1), (Rn - Rs) * math.sin(phi1))
    Pmax = (Cs[0], Cs[1] + Rs)
    psi2 = math.pi / 2 + th                       # normal angle at the cone join
    P2 = (Cs[0] - Rs * math.cos(psi2), Cs[1] + Rs * math.sin(psi2))
    if P2[1] <= rb:
        raise InvalidGeometry(
            f"shoulder/cone join radius {P2[1]:.4g} is not above closure radius {rb:.4g}")
    # virtual sharp corner of the cone with the base plane
    x_b = P2[0] + (P2[1] - rb) / math.tan(th)
    # fillet: centre at distance rf from the base plane and from the cone line (inside the body)
    nc = (math.sin(th), math.cos(th))
    x_f = x_b - rf
    y_f = P2[1] - (rf + nc[0] * (x_f - P2[0])) / nc[1]
    Cf = (x_f, y_f)
    P3 = (Cf[0] + rf * nc[0], Cf[1] + rf * nc[1])      # cone/fillet tangency
    Pf = (x_b, y_f)                                      # fillet/base tangency
    P4 = (x_b, 0.0)
    if P3[0] <= P2[0] + 1e-12 or y_f <= 0.0:
        raise InvalidGeometry("fillet does not fit between the shoulder/cone join and the axis")
    Lcone = math.hypot(P3[0] - P2[0], P3[1] - P2[1])
    if P3[1] >= P2[1]:
        raise InvalidGeometry("cone must extend aft")

    s_P1 = Rn * phi1
    s_Pmax = s_P1 + Rs * (math.pi / 2 - phi1)
    s_P2 = s_P1 + Rs * (psi2 - phi1)
    s_P3 = s_P2 + Lcone
    s_Pf = s_P3 + rf * (math.pi / 2 - th)
    s_P4 = s_Pf + y_f

    segs = [
        Segment("arc", (0.0, 0.0), P1, (Rn, 0.0), Rn, "nose_cap"),
        Segment("arc", P1, P2, Cs, Rs, "shoulder"),
        Segment("line", P2, P3, name="cone"),
        Segment("arc", P3, Pf, Cf, rf, "corner_fillet"),
        Segment("line", Pf, P4, name="base"),
    ]
    prof = CapsuleProfile(p, phi1, Cs, P1, Pmax, P2, P3, Pf, P4, Cf,
                          s_P1, s_Pmax, s_P2, s_P3, s_Pf, s_P4,
                          length=P4[0], volume=0.0, wetted_area=0.0, segments=segs)
    xy = sample_profile(prof, n_cap=400, n_shoulder=200, n_cone=200, n_base=50)
    prof.volume = enclosed_volume(xy)
    prof.wetted_area = wetted_area(xy)
    return prof


def sample_profile(prof: CapsuleProfile, n_cap=200, n_shoulder=100, n_cone=100,
                   n_base=20, n_fillet=40) -> np.ndarray:
    """Return (N, 2) array of (x, y) along the wall from the nose to the axis
    behind the base, ordered by increasing arc length."""
    p = prof.params
    Rn, Rs, Cs = p.Rn, p.Rs, prof.center_s
    phi = np.linspace(0.0, prof.phi1, n_cap)
    cap = np.column_stack([Rn - Rn * np.cos(phi), Rn * np.sin(phi)])
    psi = np.linspace(prof.phi1, math.pi / 2 + p.theta_c, n_shoulder)[1:]
    sh = np.column_stack([Cs[0] - Rs * np.cos(psi), Cs[1] + Rs * np.sin(psi)])
    t = np.linspace(0.0, 1.0, n_cone)[1:]
    cone = np.column_stack([prof.P2[0] + t * (prof.P3[0] - prof.P2[0]),
                            prof.P2[1] + t * (prof.P3[1] - prof.P2[1])])
    ang = np.linspace(math.pi / 2 - p.theta_c, 0.0, n_fillet)[1:]
    fil = np.column_stack([prof.center_f[0] + p.rf * np.cos(ang), prof.center_f[1] + p.rf * np.sin(ang)])
    t = np.linspace(0.0, 1.0, n_base)[1:]
    base = np.column_stack([np.full_like(t, prof.Pf[0]), prof.Pf[1] * (1.0 - t)])
    return np.vstack([cap, sh, cone, fil, base])


def arc_length(xy: np.ndarray) -> np.ndarray:
    d = np.hypot(np.diff(xy[:, 0]), np.diff(xy[:, 1]))
    return np.concatenate([[0.0], np.cumsum(d)])


def enclosed_volume(xy: np.ndarray) -> float:
    """Volume of revolution pi * integral y^2 dx along the closed profile."""
    x, y = xy[:, 0], xy[:, 1]
    return float(abs(math.pi * np.trapezoid(y ** 2, x)))


def wetted_area(xy: np.ndarray) -> float:
    x, y = xy[:, 0], xy[:, 1]
    ds = np.hypot(np.diff(x), np.diff(y))
    ym = 0.5 * (y[1:] + y[:-1])
    return float(2.0 * math.pi * np.sum(ym * ds))


def tangent_discontinuity_deg(xy: np.ndarray) -> float:
    """Largest turning angle between consecutive segments of a sampled
    profile, excluding the deliberate corners at the base (last two
    segments). Used by the tests to verify G1 joins."""
    d = np.diff(xy, axis=0)
    ang = np.arctan2(d[:, 1], d[:, 0])
    turn = np.abs(np.diff(np.unwrap(ang)))
    return float(np.degrees(turn.max()))


def check_profile(prof: CapsuleProfile, max_join_turn_deg: float = 2.0) -> List[str]:
    """Return a list of problems (empty list = valid)."""
    issues = []
    xy = sample_profile(prof)
    if np.any(xy[:, 1] < -1e-12):
        issues.append("negative radius")
    # self-intersection: x must be monotone along cap+shoulder+cone up to P3
    body = xy[xy[:, 1] > prof.Pf[1] - 1e-12]
    if np.any(np.diff(body[:, 0]) < -1e-12):
        issues.append("x not monotone along the body (fold-over)")
    # G1 joins everywhere (the only corner is at the axis, which is not a join)
    interior = xy[xy[:, 1] > 1e-12]
    if tangent_discontinuity_deg(interior) > max_join_turn_deg:
        issues.append("tangent discontinuity at a join")
    if abs(prof.Pmax[1] - prof.params.R) > 1e-9 * prof.params.D:
        issues.append("maximum radius does not equal D/2")
    return issues


def export_csv(prof: CapsuleProfile, path: str, **kw) -> None:
    xy = sample_profile(prof, **kw)
    s = arc_length(xy)
    with open(path, "w") as f:
        f.write("# AETHER capsule meridional profile; x axial [m], y radial [m], s arc length from nose [m]\n")
        f.write("# params: " + json.dumps(asdict(prof.params)) + "\n")
        f.write("x,y,s\n")
        for (x, y), si in zip(xy, s):
            f.write(f"{x:.9e},{y:.9e},{si:.9e}\n")


def export_json(prof: CapsuleProfile, path: str) -> None:
    with open(path, "w") as f:
        json.dump(prof.to_dict(), f, indent=2)


def export_svg(prof: CapsuleProfile, path: str, title: str = "") -> None:
    """Labelled meridional sketch (both halves) for the documentation."""
    p = prof.params
    xy = sample_profile(prof, 300, 150, 100, 10, 40)
    L, R = prof.length, p.R
    W, H = 900.0, 620.0
    sc = min((W - 260) / L, (H - 140) / (2 * R))
    ox, oy = 120.0, H / 2

    def X(x): return ox + sc * x
    def Y(y): return oy - sc * y

    def poly(pts, stroke="#111", width=2.2, dash=""):
        d = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in pts)
        da = f' stroke-dasharray="{dash}"' if dash else ""
        return f'<polyline fill="none" stroke="{stroke}" stroke-width="{width}"{da} points="{d}"/>'

    upper = xy
    lower = np.column_stack([xy[:, 0], -xy[:, 1]])
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}" font-family="Helvetica, Arial, sans-serif" font-size="14">',
           '<rect width="100%" height="100%" fill="white"/>']
    if title:
        out.append(f'<text x="{W/2:.0f}" y="28" text-anchor="middle" font-size="17" font-weight="bold">{title}</text>')
    # axis of symmetry
    out.append(f'<line x1="{X(-0.25*L):.1f}" y1="{Y(0):.1f}" x2="{X(1.15*L):.1f}" y2="{Y(0):.1f}" stroke="#555" stroke-width="1" stroke-dasharray="10,4,2,4"/>')
    out.append(f'<text x="{X(1.15*L)+4:.1f}" y="{Y(0)+5:.1f}" fill="#555">axis (x)</text>')
    out.append(poly(upper)); out.append(poly(lower))
    # nose radius construction
    out.append(f'<line x1="{X(p.Rn):.1f}" y1="{Y(0):.1f}" x2="{X(prof.P1[0]):.1f}" y2="{Y(prof.P1[1]):.1f}" stroke="#1f77b4" stroke-width="1.2" stroke-dasharray="5,4"/>')
    out.append(f'<circle cx="{X(p.Rn):.1f}" cy="{Y(0):.1f}" r="3" fill="#1f77b4"/>')
    out.append(f'<text x="{X(0.5*(p.Rn+prof.P1[0]))+6:.1f}" y="{Y(0.5*prof.P1[1])-6:.1f}" fill="#1f77b4">R_n = {p.Rn_D:.3f} D</text>')
    # shoulder radius construction
    cs = prof.center_s
    out.append(f'<line x1="{X(cs[0]):.1f}" y1="{Y(cs[1]):.1f}" x2="{X(prof.Pmax[0]):.1f}" y2="{Y(prof.Pmax[1]):.1f}" stroke="#d62728" stroke-width="1.2" stroke-dasharray="5,4"/>')
    out.append(f'<circle cx="{X(cs[0]):.1f}" cy="{Y(cs[1]):.1f}" r="3" fill="#d62728"/>')
    out.append(f'<text x="{X(prof.Pmax[0])+8:.1f}" y="{Y(prof.Pmax[1])-10:.1f}" fill="#d62728">R_s = {p.Rs_D:.4f} D</text>')
    # cone angle
    out.append(f'<line x1="{X(prof.P2[0]):.1f}" y1="{Y(prof.P2[1]):.1f}" x2="{X(prof.P2[0]+0.6*(prof.P3[0]-prof.P2[0])):.1f}" y2="{Y(prof.P2[1]):.1f}" stroke="#2ca02c" stroke-width="1.2" stroke-dasharray="5,4"/>')
    out.append(f'<text x="{X(prof.P2[0]+0.25*(prof.P3[0]-prof.P2[0]))+4:.1f}" y="{Y(prof.P2[1])-8:.1f}" fill="#2ca02c">theta_c = {p.theta_c_deg:.1f} deg (from axis)</text>')
    # diameter
    out.append(f'<line x1="{X(prof.Pmax[0])+0:.1f}" y1="{Y(R):.1f}" x2="{X(prof.Pmax[0]):.1f}" y2="{Y(-R):.1f}" stroke="#444" stroke-width="1" stroke-dasharray="3,3"/>')
    out.append(f'<text x="{X(prof.Pmax[0])-70:.1f}" y="{Y(-R)+20:.1f}" fill="#444">D = {p.D:.4f} m (fixed)</text>')
    # base radius and fillet
    out.append(f'<line x1="{X(prof.P4[0])+10:.1f}" y1="{Y(0):.1f}" x2="{X(prof.P4[0])+10:.1f}" y2="{Y(p.rb):.1f}" stroke="#9467bd" stroke-width="1.2"/>')
    out.append(f'<text x="{X(prof.P4[0])+16:.1f}" y="{Y(0.5*p.rb)+5:.1f}" fill="#9467bd">r_b = {p.rb_D:.2f} D (fixed)</text>')
    out.append(f'<circle cx="{X(prof.center_f[0]):.1f}" cy="{Y(prof.center_f[1]):.1f}" r="2.5" fill="#8c564b"/>')
    out.append(f'<text x="{X(prof.center_f[0])-120:.1f}" y="{Y(prof.center_f[1])+5:.1f}" fill="#8c564b" font-size="12">r_f = {p.rf_D:.2f} D (fixed)</text>')
    # length
    out.append(f'<line x1="{X(0):.1f}" y1="{Y(-R)-30:.1f}" x2="{X(L):.1f}" y2="{Y(-R)-30:.1f}" stroke="#444" stroke-width="1"/>')
    out.append(f'<text x="{X(0.5*L):.1f}" y="{Y(-R)-36:.1f}" text-anchor="middle" fill="#444">L = {L/p.D:.3f} D (derived)</text>')
    # join labels
    for name, pt in (("P1 cap/shoulder", prof.P1), ("P2 shoulder/cone", prof.P2), ("P3 cone/fillet", prof.P3), ("Pf fillet/base", prof.Pf)):
        out.append(f'<circle cx="{X(pt[0]):.1f}" cy="{Y(pt[1]):.1f}" r="3" fill="#111"/>')
        out.append(f'<text x="{X(pt[0])+6:.1f}" y="{Y(pt[1])+16:.1f}" font-size="12">{name}</text>')
    out.append(f'<text x="{X(0)-8:.1f}" y="{Y(0)-10:.1f}" text-anchor="end" font-size="12">nose, s = 0</text>')
    out.append(f'<text x="20" y="{H-18:.0f}" font-size="12" fill="#333">Flow is in +x. Heat-flux objective evaluated on nose cap + shoulder (s from 0 to P2). Drag integrated over the whole body.</text>')
    out.append("</svg>")
    with open(path, "w") as f:
        f.write("\n".join(out))


def apollo_045_scale() -> CapsuleParams:
    """Clean Apollo command module, 0.045-scale AEDC Tunnel C model
    (NASA TM X-1243, Fig. 1b): max radius 3.46 in, nose radius 8.32 in,
    toroid radius 0.35 in, cone half-angle 33 deg. The rear closure is
    replaced by the project's filleted flat base (r_b = 0.20 D, r_f = 0.03 D)."""
    inch = 0.0254
    D = 2 * 3.46 * inch
    return CapsuleParams(D=D, Rn_D=8.32 / 6.92, Rs_D=0.35 / 6.92, theta_c_deg=33.0, rb_D=0.20, rf_D=0.03)


if __name__ == "__main__":
    import sys
    p = apollo_045_scale()
    prof = build_profile(p)
    print(json.dumps({k: v for k, v in prof.to_dict().items() if k != "segments"}, indent=1))
    print("S/R at cap-shoulder tangency:", prof.s_P1 / p.R)
    print("S/R at maximum radius:", prof.s_Pmax / p.R)
    print("issues:", check_profile(prof))
    if len(sys.argv) > 1:
        export_svg(prof, sys.argv[1], "AETHER capsule family: baseline (Apollo 0.045-scale clean geometry)")
