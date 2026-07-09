---
title: "Project AETHER"
subtitle: "Shape versus drag and heating of a re-entry capsule heat shield"
author: "Adithya Kesan Jayakanth"
date: "August 2026"
---

# The question

- A capsule needs drag to slow down and must survive the heating that comes with it.
- Three shape parameters: nose radius R_n/D, shoulder radius R_s/D, cone half-angle θ_c.
- One fixed condition: Mach 10.18, Re_D = 1.1 × 10⁶, cold wall (the Apollo Tunnel C test of NASA TM X-1243).
- Two objectives: maximise C_D, minimise the peak heat flux on the heat shield.

# From STEM F1 Racing to AETHER

- Same method: parameterise a shape, simulate, compare, decide, explain.
- New physics: a bow shock, a thin thermal boundary layer, drag that is now useful.
- New discipline: every number traced to a mesh, a configuration and a convergence check.

# Geometry family

![Baseline capsule and its parameters](../figure_geometry_baseline.svg)

- Tangent joins; the aft length follows from the closure rule.
- Baseline = clean Apollo model: landmarks of the reference report reproduced to 0.002 in S/R.
- Invalid shapes (shoulder or fillet that does not fit) are rejected and recorded.

# Mesh and solver

- Body-fitted structured mesh built from the parameter table; three nested levels (÷1.5).
- SU2 v8.5.0, laminar Navier–Stokes, axisymmetric, isothermal wall.
- What I had to find out the hard way:
  - an axis defect in SU2's axisymmetric mode (patched, verified on a sphere);
  - the carbuncle instability and a two-branch solution — fixed by a Roe start-up and a SLAU2 restart;
  - second order never stationary in axisymmetric mode — first order plus a mesh study instead.

# Validation

![Cylinder benchmark](../../results/figures/validation_cylinder.png)

RESULTS_SLIDE_VALIDATION

# Validation — Apollo at α = 0

![Apollo pressure and heating distributions](../../results/figures/validation_apollo.png)

# Mesh convergence

![Mesh study](../../results/figures/mesh_study.png)

RESULTS_SLIDE_MESH

# Trade space

![Drag versus peak heating](../../results/figures/pareto.png)

RESULTS_SLIDE_PARETO

# Sensitivities

![One-variable sensitivities](../../results/figures/sensitivities.png)

RESULTS_SLIDE_SENS

# What the flow looks like

RESULTS_SLIDE_FIELDS

# Conclusions

RESULTS_SLIDE_CONCLUSIONS

# Limitations and next steps

- Perfect gas, laminar, one condition, wind-tunnel scale; wake excluded (bounded).
- First-order convective fluxes in the axisymmetric runs: uncertainty quantified, not removed.
- Next: second condition (Mach 8 Apollo data), second-order once SU2's axisymmetric mode allows it, finer shoulder study.
