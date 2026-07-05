# Mesh generation

*Project AETHER — mesh definition frozen 19 June 2026 after the numerical investigation recorded in docs/validation.md and docs/logbook.md.*

## Topology

All meshes are single-block, body-fitted structured quadrilateral grids written directly in SU2's native format by `aether/mesh.py`. The grid is generated from the same parameter table as the geometry, so every candidate shape gets a mesh built by identical rules.

**Capsule (axisymmetric half-plane).** The wall runs from the nose stagnation point over the cap, shoulder and cone to the cone end P₃. Grid lines leave the wall along the local wall normal (orthogonal cells through the boundary layer) and are progressively smoothed outward so that they fan around the shoulder without crossing; the first line is the upstream axis of symmetry (`axis`), the last line is the outlet plane normal to the cone at its end (`outflow`, supersonic outlet). The outer boundary (`farfield`) is a smooth closed curve: a circle of radius 2 D + L/2 about the body mid-length upstream, continued by an ellipse downstream; grid lines are intersected with it so the boundary is exactly on the curve. Away from the wall, the inherited wall clustering is relaxed toward uniform spacing along each grid level (85 % at the far boundary), which removes the dense bands that wall clustering otherwise projects into the far field.

**Why the domain ends at the cone end.** The flat base and wake are excluded (`truncate_at_base`). At M = 10.18 the base pressure force is bounded by p_base ∈ [0, p∞], i.e. ΔC_D ≤ (2/γM²)(r_b/R)² = 0.0006, far below the mesh uncertainty of C_D; the laminar near wake, on the other hand, is unsteady and in test runs (logbook, 15–16 June 2026) fed a limit cycle back into the whole solution. The outlet plane lies in the supersonic expansion over the cone end where extrapolation is appropriate; the fillet is retained as part of the closure definition for geometry bookkeeping (volume, length) and is the end of the modelled wall.

**Cylinder (planar, Benchmark A).** Polar grid between the cylinder surface and a concentric far boundary at 3 R, from the stagnation line (`symmetry`) to θ = 105° (`outflow`); exactly orthogonal. The comparison with the experiment uses 0–90°, so the outlet is one expansion-fan width downstream of the last comparison station.

## Spacing rules and refinement family

| Quantity | Capsule (base) | Cylinder (base) |
|---|---|---|
| First cell height at the wall | 4.5 µm | 1.5 µm |
| Normal growth ratio in the boundary-layer block | 1.22 | 1.18 |
| Uniform normal spacing through the shock region | 1.2 mm out to 0.45 D | 0.375 mm out to 0.7 R |
| Stretched cells to the far boundary | 24 (ratio ≈ 1.15) | 20 |
| Wall spacing: nose cap / shoulder / cone | 1.2 / 0.45 / 1.65 mm | 1.13° (0.75 mm) |
| Cells (baseline geometry) | 22 035 | 10 974 |

The estimated stagnation-region thermal layer is 0.4 mm thick on the capsule and 0.12 mm on the cylinder (Fay–Riddell velocity gradient); the base first-cell heights place 17–20 cells inside it.

**Refinement family (coarse / medium / fine).** The levels refine the *wall-normal boundary-layer resolution* only: the first-cell height is divided by 1.5 per level (4.5 → 3.0 → 2.0 µm on the capsule, 1.5 → 1.0 → 0.67 µm on the cylinder) and the growth ratio is reduced so that the number of cells across a fixed layer thickness scales by the same factor (1.22 → 1.15 → 1.10). The wall-tangential and shock-region spacings are identical at every level. This is a nested family with refinement ratio r = 1.5 for the quantity that governs the wall heat flux (the wall-normal temperature gradient), and it is what the Richardson/GCI analysis in `aether/convergence.py` is applied to.

**Why the shock-region spacing is held fixed.** Refining the tangential and shock-normal spacings by 1.5 (`refine_mode = "all"`) re-triggers the stagnation-line instability of the first-order upwind solution — a heating spike at the stagnation node of +70 % on the planar cylinder and a stagnation pressure 15–30 % above the pitot value on the axisymmetric capsule — with every flux function available in SU2 (docs/validation.md C.1). The base spacing (1.2 mm on the capsule, 0.375 mm on the cylinder, aspect ratio ≈ 1–2 at the shock) is the finest at which the solution is stationary, free of the anomaly and in agreement with the measured pressure and heating distributions. The influence of the shock-region spacing on the objectives is therefore assessed separately, by comparison of the base spacing with a coarser one (1.6 mm) at the base boundary-layer resolution, and reported as an additional uncertainty rather than folded into the Richardson estimate.

## Quality metrics (written to `mesh_report.json` of every case)

Signed cell area (no inverted cell allowed), minimum and maximum interior angle, maximum aspect ratio, first-cell height range, cell and point counts. Baseline base level: minimum angle 65°, maximum angle 116°, maximum aspect ratio ≈ 270 (boundary-layer cells; expected and intended), no inverted cells. Every sweep case must pass the same checks before the solver is called; a failing mesh is recorded as an invalid case.

## Far-boundary check

`cases/domain_check/base_far` repeats the baseline at the base level with the far boundary moved from 2.0 D to 3.0 D at the nose and from 4.5 D to 7.0 D downstream. The change in C_D and q''_max is reported in docs/validation.md and must be smaller than the mesh uncertainty for the chosen domain to be accepted.

## Gmsh

Gmsh 4.15.2 is installed in the environment and was evaluated for an unstructured alternative (triangles with a quadrilateral boundary-layer field). It was not adopted because (i) laminar hypersonic heat flux is set by the wall-normal temperature gradient across a sub-millimetre layer, for which wall-orthogonal, smoothly growing quadrilaterals are the standard and most reliable discretisation; (ii) nested refinement by an exact factor is straightforward for the structured generator and is what the Richardson analysis assumes; (iii) the structured generator produces every candidate shape from the parameter table with no manual intervention. The SU2 `navierstokes/sphere` test case's Gmsh script in the SU2 repository was used as the reference for marker naming and SU2 export conventions.
