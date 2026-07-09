---
title: "Project AETHER — Multi-Objective Shape Study of a Hypersonic Re-entry Capsule Heat Shield"
subtitle: "Aerodynamic Evaluation of Thermal Hazards in Entry Regimes"
author: "Adithya Kesan Jayakanth"
date: "August 2026"
abstract: |
  RESULTS_ABSTRACT
---

# Introduction

A blunt capsule entering the atmosphere must produce enough aerodynamic drag to decelerate while limiting the convective heating of its heat shield. Both quantities are set by the external shape at a given flight condition, and they do not have to move together: a flatter nose raises drag and spreads the heating over a larger surface, while the shoulder that joins the face to the afterbody concentrates heating where the boundary layer is thinnest. This study asks a bounded version of that question:

> How do nose radius, shoulder radius and rear-body cone half-angle affect the drag coefficient and the peak surface heat flux of an Apollo-like axisymmetric capsule at one fixed hypersonic condition?

The study keeps the maximum diameter, the reference area and the free-stream condition fixed, varies the three shape parameters one at a time and then in combination, computes drag and wall heat flux with laminar compressible Navier–Stokes simulations, and reports the nondominated set of shapes with the numerical uncertainty needed to say whether two shapes actually differ. Heat-shield thickness, ablation, trajectory integration and high-temperature chemistry are outside the scope.

# Method

## Condition and reference data

The simulations reproduce the clean Apollo command module test of NASA TM X-1243 (Bertin, 1966) at zero angle of attack in AEDC Tunnel C: Mach 10.18, Reynolds number 1.1 × 10⁶ based on the model diameter D = 0.1758 m, laminar flow. The report gives the measured pressure (p/p_t vs S/R) and heating (q/q_t vs S/R) distributions over the heat shield and the model geometry, which is also the baseline shape of the study. Because the run's stagnation temperature is not quoted, T₀ = 1056 K (1900 °R) is taken from the facility envelope and the wall is a 300 K cold wall; the derived free stream is in `docs/conditions.md`. A second, planar benchmark — Run 31 of NASA TM 100484 (Wieting, 1987), a 3-inch cylinder at Mach 8.03 with tabulated surface pressure and heat flux — is used to check the solver's wall heat-flux prediction independently of the axisymmetric treatment.

The gas is calorically perfect air with Sutherland viscosity and a constant laminar Prandtl number of 0.72. At the main condition the post-shock temperature reaches 1056 K, where vibrational excitation changes the specific heats by a few percent and dissociation is negligible; at the cylinder condition it reaches 1736 K (perfect gas) against the 1583 K of the thermally perfect tunnel calibration. These are stated limitations of the heating comparison, not of the ranking between shapes at the same condition.

## Geometry

The capsule profile (`docs/geometry.md`) is a spherical nose cap of radius R_n, a toroidal shoulder of radius R_s reaching the fixed maximum radius D/2, a straight cone at half-angle θ_c, and a fixed closure (base radius 0.20 D with a 0.03 D corner fillet). All joins are tangent-continuous, the total length follows from the closure rule, and shapes failing the validity rules (shoulder that does not fit, fillet that does not fit, fold-over) are rejected and recorded. The baseline (R_n/D = 1.202, R_s/D = 0.0506, θ_c = 33°) reproduces the tangency and maximum-radius landmarks quoted in the reference report to within 0.002 in S/R.

## Mesh and solver

Body-fitted structured meshes are generated from the same parameter table (`docs/mesh.md`): wall-orthogonal boundary-layer cells (first cell 3 µm, growth 1.15), uniform 0.8 mm cells through the shock region, a smooth far boundary at 2 D ahead of the nose, and an outlet plane normal to the cone at its end. The base and near wake are excluded: at Mach 10 the base pressure force is bounded by ΔC_D ≤ 0.0006, below the mesh uncertainty, while the laminar near wake is unsteady and in test runs fed a limit cycle into the whole field. Three nested levels (every spacing ÷ 1.5 per level) support a Richardson extrapolation of the baseline results.

The flow solver is SU2 v8.5.0 built from source with one source patch: the near-axis treatment of the axisymmetric source terms proposed in SU2 pull request #2715. Without it, SU2's axisymmetric mode produces an unphysical heating dip at the stagnation line (a sphere test on the validated cylinder mesh drops from 504 to 154 kW/m² at the second wall node against a 640–705 plateau), a defect also reported in SU2 issues #1373 and #2438; with the patch the profile is monotone and the residual converges to 10⁻⁹. Each case is run in stages on the same mesh: a Roe start-up with a large entropy fix (carbuncle-free, converges strongly, but with an unusable boundary-layer heat flux), then SLAU2 first order restarted from it, which converges to the physical, carbuncle-free branch at every level. Second-order reconstruction is used only for the planar benchmark, because in axisymmetric mode it never reaches a stationary state with this SU2 version whatever the flux, limiter or CFL (`docs/validation.md` A.4); the first-order discretisation error is quantified by the mesh study and by the first/second-order comparison on the cylinder.

Wall heat flux and pressure are read at the wall nodes of the volume solution and cross-checked against the first-cell temperature gradient (within 3 %). A case counts as converged when SU2's Cauchy criterion on drag and the heat-flux monitor stops it and the post-processor finds drag flat to 0.1 % and the heat-flux monitor flat to 1 % over the last 500 iterations, with the wall-node peak heat flux changed by less than 0.2 % between the last two solution snapshots.

## Objectives, sweep and selection rule

The objectives are the whole-body drag coefficient (reference area πD²/4 for every shape) and the maximum wall heat flux over the heat-shield surface, defined as the nose cap plus the shoulder up to the shoulder/cone tangency. The sweep (`configs/sweep.yaml`) varies R_n/D over 0.6–1.6, θ_c over 25–41° and R_s/D over 0.03–0.18 one at a time about the baseline, adds five combinations, and includes two deliberately invalid shapes. The preferred compromise is selected by an explicit rule — the lowest peak heat flux among designs with C_D ≥ 0.98 C_D,baseline — and two alternative rules (0.95 and 1.00) are reported for sensitivity. Two designs are called different only if their objectives differ by more than the numerical uncertainty from the mesh study.

# Verification and validation

RESULTS_VALIDATION

# Results

RESULTS_MAIN

# Discussion

RESULTS_DISCUSSION

# Limitations

RESULTS_LIMITATIONS

# Conclusions

RESULTS_CONCLUSIONS

# Reproducibility

Every number in this report is produced by `make all` from the repository (`README.md`): meshes, configurations, solver logs, convergence histories, wall profiles and summaries are kept per case under `cases/`, and `results/results.csv` lists every case including the failed and the rejected ones. Software versions are recorded in `docs/versions.md`; the solver patch is `tools/pr2715.diff`.

# References

1. Bertin, J. J., *The Effect of Protuberances, Cavities, and Angle of Attack on the Wind-Tunnel Pressure and Heat-Transfer Distribution for the Apollo Command Module*, NASA TM X-1243, 1966.
2. Wieting, A. R., *Experimental Study of Shock Wave Interference Heating on a Cylindrical Leading Edge*, NASA TM 100484, 1987.
3. Economon, T. D., Palacios, F., Copeland, S. R., Lukaczyk, T. W., Alonso, J. J., "SU2: An Open-Source Suite for Multiphysics Simulation and Design", *AIAA Journal* 54(3), 2016. SU2 v8.5.0, https://su2code.github.io.
4. Kitamura, K., Shima, E., "Towards shock-stable and accurate hypersonic heating computations: A new pressure flux for AUSM-family schemes", *J. Comput. Phys.* 245, 2013 (SLAU2).
5. Fay, J. A., Riddell, F. R., "Theory of Stagnation Point Heat Transfer in Dissociated Air", *J. Aeronaut. Sci.* 25(2), 1958.
6. Lees, L., "Laminar Heat Transfer over Blunt-Nosed Bodies at Hypersonic Flight Speeds", *Jet Propulsion* 26(4), 1956.
7. Celik, I. B., Ghia, U., Roache, P. J., Freitas, C. J., Coleman, H., Raad, P. E., "Procedure for Estimation and Reporting of Uncertainty Due to Discretization in CFD Applications", *J. Fluids Eng.* 130(7), 2008.
8. Anderson, J. D., *Hypersonic and High-Temperature Gas Dynamics*, 2nd ed., AIAA, 2006.
9. SU2 pull request #2715, "Axisymmetric near-axis fixes using L'Hôpital-consistent formulations", https://github.com/su2code/SU2/pull/2715; SU2 issues #1373 and #2438.
