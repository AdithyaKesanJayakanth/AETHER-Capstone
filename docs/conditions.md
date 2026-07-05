# Operating conditions

All simulations: calorically perfect air (gamma 1.4, R 287.058 J/kg/K), Sutherland viscosity (mu_ref 1.716e-5 Pa s at 273.15 K, S 110.4 K), laminar, constant Prandtl number 0.72. Densities and pressures are what SU2 computes from the Mach number, static pressure and static temperature given in the configuration files.

## Main study condition (capsule family) — Benchmark B

Clean Apollo CM in AEDC Tunnel C (NASA TM X-1243): M = 10.18, Re_D = 1.10e+06, D = 0.17577 m (0.045-scale model). Stagnation temperature taken as 1055.6 K (1900 R), within the facility envelope of 1650-1950 R; the report does not quote the run's T0. Cold isothermal wall at 300 K.

| Quantity | Value | Unit |
|---|---:|---|
| Mach number | 10.18 | - |
| Freestream static temperature | 48.59 | K |
| Freestream static pressure | 190.55 | Pa |
| Freestream density | 0.01366 | kg/m^3 |
| Freestream velocity | 1422.5 | m/s |
| Freestream viscosity (Sutherland) | 3.106e-06 | Pa s |
| Stagnation temperature (perfect gas) | 1055.6 | K |
| Isentropic stagnation pressure | 9.109 | MPa |
| Pitot pressure behind normal shock | 25514.1 | Pa |
| Unit Reynolds number | 6.2582e+06 | 1/m |
| Reference length | 0.17577 | m |
| Reynolds number (reference length) | 1.1000e+06 | - |
| Wall temperature (isothermal) | 300.00 | K |
| Dynamic pressure 0.5 rho U^2 | 13823.4 | Pa |

Fay-Riddell stagnation-point heat flux estimate for the baseline nose radius (R_n = 0.2113 m): 84.6 kW/m^2 (perfect gas, Le = 1, Newtonian velocity gradient). This is a sanity check for the order of magnitude, not validation data.

## Benchmark A (solver heating check, planar) — Wieting Run 31

Calspan 48-inch HST, undisturbed 3-inch cylinder (NASA TM 100484, Table 11, Run 31): M = 8.03, p_inf = 855.0 Pa (0.124 psia), T_inf = 124.94 K (224.9 R), wall 294.44 K (530 R). Given p and T directly, SU2's Sutherland viscosity yields the Reynolds number below; the report's value is 1.468e6 /ft = 4.816e6 /m (1.835e5 on the radius), 2 % lower than Sutherland.

| Quantity | Value | Unit |
|---|---:|---|
| Mach number | 8.03 | - |
| Static temperature | 124.94 | K |
| Static pressure | 855.0 | Pa |
| Density | 0.02384 | kg/m^3 |
| Velocity | 1799.3 | m/s |
| Viscosity (Sutherland) | 8.652e-06 | Pa s |
| Reynolds number on radius 0.0381 m | 1.889e+05 | - |
| Pitot pressure (Rayleigh) | 71375 | Pa |
| Report P0 (Run 31) | 72190 | Pa |
| Report Q0 (Run 31) | 7.210e+05 | W/m^2 |
| Wall temperature | 294.44 | K |

## Limits of the gas model

- Freestream static temperatures are 49 K (main) and 125 K (cylinder); Sutherland's law is extrapolated below its usual 100 K lower limit for the main condition. Near the body the gas is at post-shock temperatures (up to T0), where the law is well within range.
- Post-shock stagnation temperatures of 1056 K (main) and 1736 K (cylinder, perfect gas) excite molecular vibration; Wieting reports T_T = 1583 K for Run 31 from the thermally perfect tunnel calibration. Dissociation is negligible at both conditions. The calorically perfect assumption therefore over-predicts post-shock temperature by a few percent for the main condition and by about 10 % for the cylinder; this is a stated limitation of the heating comparison.
- No turbulence model: both reference experiments report laminar flow at these Reynolds numbers.
