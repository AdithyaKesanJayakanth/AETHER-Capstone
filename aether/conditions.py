"""Freestream condition derivation and classical estimates.

Everything here is perfect gas (calorically perfect air, gamma = 1.4,
R = 287.058 J/kg/K) with Sutherland viscosity and a constant laminar
Prandtl number. These are exactly the models SU2 is configured with, so
the numbers written by this module are the numbers the solver sees.

Two classical estimates are provided as sanity checks, not as validation:

* Fay-Riddell stagnation-point heat flux (perfect gas, Lewis number 1,
  no dissociation) with the Newtonian stagnation velocity gradient.
* Modified-Newtonian pressure and forebody drag coefficient.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

GAMMA = 1.4
R_AIR = 287.058          # J/(kg K)
PR_LAM = 0.72
# Sutherland constants for air (SU2 defaults: MU_REF, MU_T_REF, SUTHERLAND_CONSTANT)
MU_REF = 1.716e-5        # Pa s
T_MU_REF = 273.15        # K
S_SUTH = 110.4           # K
CP_AIR = GAMMA * R_AIR / (GAMMA - 1.0)

BTU_FT2_S = 11356.5      # W/m^2 per Btu/(ft^2 s)
PSIA = 6894.757          # Pa per psia
INCH = 0.0254            # m per inch
RANKINE = 5.0 / 9.0      # K per degree Rankine


def sutherland(T: float) -> float:
    """Dynamic viscosity of air [Pa s] by Sutherland's law."""
    return MU_REF * (T / T_MU_REF) ** 1.5 * (T_MU_REF + S_SUTH) / (T + S_SUTH)


def speed_of_sound(T: float) -> float:
    return math.sqrt(GAMMA * R_AIR * T)


def total_temperature_ratio(M: float) -> float:
    return 1.0 + 0.5 * (GAMMA - 1.0) * M * M


def pitot_pressure_ratio(M: float) -> float:
    """Rayleigh pitot formula: p_t2 / p_inf for M > 1."""
    g = GAMMA
    a = ((g + 1.0) * M * M / 2.0) ** (g / (g - 1.0))
    b = ((g + 1.0) / (2.0 * g * M * M - (g - 1.0))) ** (1.0 / (g - 1.0))
    return a * b


def normal_shock_static_ratio(M: float) -> float:
    g = GAMMA
    return 1.0 + 2.0 * g / (g + 1.0) * (M * M - 1.0)


@dataclass
class Freestream:
    name: str
    mach: float
    T_inf: float          # K
    p_inf: float          # Pa
    rho_inf: float        # kg/m^3
    U_inf: float          # m/s
    mu_inf: float         # Pa s
    T0: float             # K (stagnation, perfect gas)
    p0: float             # Pa (isentropic stagnation, upstream of shock)
    p_t2: float           # Pa (pitot pressure behind normal shock)
    Re_per_m: float
    ref_length: float     # m
    Re_ref: float
    T_wall: float         # K
    q_dyn: float          # Pa, 0.5 rho U^2

    def table_markdown(self) -> str:
        rows = [
            ("Mach number", f"{self.mach:.2f}", "-"),
            ("Freestream static temperature", f"{self.T_inf:.2f}", "K"),
            ("Freestream static pressure", f"{self.p_inf:.2f}", "Pa"),
            ("Freestream density", f"{self.rho_inf:.5f}", "kg/m^3"),
            ("Freestream velocity", f"{self.U_inf:.1f}", "m/s"),
            ("Freestream viscosity (Sutherland)", f"{self.mu_inf:.3e}", "Pa s"),
            ("Stagnation temperature (perfect gas)", f"{self.T0:.1f}", "K"),
            ("Isentropic stagnation pressure", f"{self.p0/1e6:.3f}", "MPa"),
            ("Pitot pressure behind normal shock", f"{self.p_t2:.1f}", "Pa"),
            ("Unit Reynolds number", f"{self.Re_per_m:.4e}", "1/m"),
            ("Reference length", f"{self.ref_length:.5f}", "m"),
            ("Reynolds number (reference length)", f"{self.Re_ref:.4e}", "-"),
            ("Wall temperature (isothermal)", f"{self.T_wall:.2f}", "K"),
            ("Dynamic pressure 0.5 rho U^2", f"{self.q_dyn:.1f}", "Pa"),
        ]
        out = [f"| Quantity | Value | Unit |", "|---|---:|---|"]
        out += [f"| {a} | {b} | {c} |" for a, b, c in rows]
        return "\n".join(out)


def freestream_from_T0(name: str, mach: float, T0: float, Re_ref: float,
                       ref_length: float, T_wall: float) -> Freestream:
    """Condition defined by (M, T0, Re based on ref_length). Typical for
    cold hypersonic wind tunnels where T0 and Re are the quoted quantities."""
    T_inf = T0 / total_temperature_ratio(mach)
    return _freestream(name, mach, T_inf, Re_ref, ref_length, T_wall)


def freestream_from_Tinf(name: str, mach: float, T_inf: float, Re_ref: float,
                         ref_length: float, T_wall: float) -> Freestream:
    return _freestream(name, mach, T_inf, Re_ref, ref_length, T_wall)


def freestream_from_pT(name: str, mach: float, p_inf: float, T_inf: float,
                       ref_length: float, T_wall: float) -> Freestream:
    """Condition defined directly by static pressure and temperature (what
    the solver is given); the Reynolds number follows from Sutherland."""
    rho = p_inf / (R_AIR * T_inf)
    U = mach * speed_of_sound(T_inf)
    mu = sutherland(T_inf)
    Re_per_m = rho * U / mu
    T0 = T_inf * total_temperature_ratio(mach)
    p0 = p_inf * total_temperature_ratio(mach) ** (GAMMA / (GAMMA - 1.0))
    p_t2 = p_inf * pitot_pressure_ratio(mach)
    return Freestream(name, mach, T_inf, p_inf, rho, U, mu, T0, p0, p_t2,
                      Re_per_m, ref_length, Re_per_m * ref_length, T_wall, 0.5 * rho * U * U)


def _freestream(name, mach, T_inf, Re_ref, ref_length, T_wall) -> Freestream:
    U = mach * speed_of_sound(T_inf)
    mu = sutherland(T_inf)
    Re_per_m = Re_ref / ref_length
    rho = Re_per_m * mu / U
    p = rho * R_AIR * T_inf
    T0 = T_inf * total_temperature_ratio(mach)
    p0 = p * total_temperature_ratio(mach) ** (GAMMA / (GAMMA - 1.0))
    p_t2 = p * pitot_pressure_ratio(mach)
    return Freestream(name, mach, T_inf, p, rho, U, mu, T0, p0, p_t2,
                      Re_per_m, ref_length, Re_ref, T_wall, 0.5 * rho * U * U)


def fay_riddell_stagnation(fs: Freestream, nose_radius: float,
                           axisymmetric: bool = True) -> float:
    """Fay-Riddell stagnation heat flux [W/m^2], perfect gas, Le = 1,
    no dissociation, Newtonian velocity gradient (du_e/dx) = (1/R_n) sqrt(2 (p_e - p_inf)/rho_e).

    Coefficient 0.763 for axisymmetric stagnation point, 0.570 for a 2-D
    cylinder (Fay & Riddell 1958; Anderson, Hypersonic and High-Temperature
    Gas Dynamics, eq. 6.108 and the planar analogue)."""
    p_e = fs.p_t2
    T_e = fs.T0
    rho_e = p_e / (R_AIR * T_e)
    mu_e = sutherland(T_e)
    rho_w = p_e / (R_AIR * fs.T_wall)
    mu_w = sutherland(fs.T_wall)
    dudx = math.sqrt(2.0 * (p_e - fs.p_inf) / rho_e) / nose_radius
    h0 = CP_AIR * T_e
    hw = CP_AIR * fs.T_wall
    coeff = 0.763 if axisymmetric else 0.570
    return (coeff * PR_LAM ** (-0.6) * math.sqrt(rho_e * mu_e)
            * (rho_w * mu_w / (rho_e * mu_e)) ** 0.1 * math.sqrt(dudx) * (h0 - hw))


def modified_newtonian_cp_max(mach: float) -> float:
    """C_p at the stagnation point from the pitot pressure."""
    g = GAMMA
    return 2.0 / (g * mach * mach) * (pitot_pressure_ratio(mach) - 1.0)


def summary_dict(fs: Freestream, nose_radius: float, axisymmetric: bool = True) -> dict:
    d = asdict(fs)
    d["fay_riddell_q_stag_W_m2"] = fay_riddell_stagnation(fs, nose_radius, axisymmetric)
    d["cp_max_modified_newtonian"] = modified_newtonian_cp_max(fs.mach)
    return d
