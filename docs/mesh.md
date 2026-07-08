# Mesh generation

*Project AETHER — mesh definition frozen 19 June 2026 after the numerical investigation recorded in docs/validation.md and docs/logbook.md.*

## Topology

All meshes are single-block, body-fitted structured quadrilateral grids written directly in SU2's native format by `aether/mesh.py`. The grid is generated from the same parameter table as the geometry, so every candidate shape gets a mesh built by identical rules.

**Capsule (axisymmetric half-plane).** The wall runs from the nose stagnation point over the cap, shoulder and cone to the cone end P₃. Grid lines leave the wall along the local wall normal (orthogonal cells through the boundary layer) and are progressively smoothed outward so that they fan around the shoulder without crossing; the first line is the upstream axis of symmetry (`axis`), the last line is the outlet plane normal to the cone at its end (`outflow`, supersonic outlet). The outer boundary (`farfield`) is a smooth closed curve: a circle of radius 2 D + L/2 about the body mid-length upstream, continued by an ellipse downstream; grid lines are intersected with it so the boundary is exactly on the curve. Away from the wall, the inherited wall clustering is relaxed toward uniform spacing along each grid level (85 % at the far boundary), which removes the dense bands that wall clustering otherwise projects into the far field.

**Why the domain ends at the cone end.** The flat base and wake are excluded (`truncate_at_base`). At M = 10.18 the base pressure force is bounded by p_base ∈ [0, p∞], i.e. ΔC_D ≤ (2/γM²)(r_b/R)² = 0.0006, far below the mesh uncertainty of C_D; the laminar near wake, on the other hand, is unsteady and in test runs (logbook, 15–16 June 2026) fed a limit cycle back into the whole solution. The outlet plane lies in the supersonic expansion over the cone end where extrapolation is appropriate; the fillet is retained as part of the closure definition for geometry bookkeeping (volume, length) and is the end of the modelled wall.

**Cylinder (planar, Benchmark A).** Polar grid between the cylinder surface and a concentric far boundary at 3 R, from the stagnation line (`symmetry`) to θ = 105° (`outflow`); exactly orthogonal. The comparison with the experiment uses 0–90°, so the outlet is one expansion-fan width downstream of the last comparison station.

## Spacing rules and refinement family

| Quantity | Capsule (coarse = base) | Cylinder (coarse = base) |
|---|---|---|
| First cell height at the wall | 3.0 µm | 1.0 µm |
| Normal growth ratio in the boundary-layer block | 1.15 | 1.12 |
| Uniform normal spacing through the shock region | 0.8 mm out to 0.45 D | 0.25 mm out to 0.7 R |
| Stretched cells to the far boundary | 24 (ratio ≈ 1.15) | 20 |
| Wall spacing: nose cap / shoulder / cone | 0.8 / 0.3 / 1.1 mm | 0.75° (0.5 mm) |
| Cells (baseline geometry) | 45 552 / 101 616 / 228 636 | 23 380 / 52 290 / 117 180 |

The estimated stagnation-region thermal layer is 0.4 mm thick on the capsule and 0.12 mm on the cylinder (Fay–Riddell velocity gradient); the base first-cell heights place about 25 cells inside it.

**Refinement family (coarse / medium / fine).** Every spacing is divided by 1.5 per level (first cell 3.0 → 2.0 → 1.33 µm on the capsule; the growth ratio is reduced so that the number of cells across a fixed layer thickness scales by the same factor: 1.15 → 1.10 → 1.067); the cell count grows by about 2.25 per level. This is a nested family with refinement ratio r = 1.5, as the Richardson/GCI analysis in `aether/convergence.py` assumes. The design sweep is run on the coarse (base) level; the baseline and the finalists are run on all three.

**Start-up procedure.** The first-order SLAU2 solution of this problem has two steady branches on every level tested: the physical one and a carbuncle branch (stagnation pressure above the pitot value, heating spike at the stagnation line). Which branch a run converges to depends on the start-up transient, not on the mesh quality: a coarser 1.2 mm family that is clean from a uniform free-stream start on one far-field stretching locks into the carbuncle branch on another. The production procedure therefore establishes the field with a Roe flux and a large entropy fix (carbuncle-free, strongly convergent) and restarts SLAU2 from it (docs/validation.md A.2); with this procedure the solution is on the physical branch at every level of the family.

## Quality metrics (written to `mesh_report.json` of every case)

Signed cell area (no inverted cell allowed), minimum and maximum interior angle, maximum aspect ratio, first-cell height range, cell and point counts. Baseline coarse level: minimum angle 45°, maximum angle 135°, maximum aspect ratio ≈ 270 (boundary-layer cells; expected and intended), no inverted cells. Every sweep case must pass the same checks before the solver is called; a failing mesh is recorded as an invalid case.

## Far-boundary check

`cases/domain_check/base_far` repeats the baseline at the coarse level with the far boundary moved from 2.0 D to 3.0 D at the nose and from 4.5 D to 7.0 D downstream. The change in C_D and q''_max is reported in docs/validation.md and must be smaller than the mesh uncertainty for the chosen domain to be accepted.

## Gmsh

Gmsh 4.15.2 is installed in the environment and was evaluated for an unstructured alternative (triangles with a quadrilateral boundary-layer field). It was not adopted because (i) laminar hypersonic heat flux is set by the wall-normal temperature gradient across a sub-millimetre layer, for which wall-orthogonal, smoothly growing quadrilaterals are the standard and most reliable discretisation; (ii) nested refinement by an exact factor is straightforward for the structured generator and is what the Richardson analysis assumes; (iii) the structured generator produces every candidate shape from the parameter table with no manual intervention. The SU2 `navierstokes/sphere` test case's Gmsh script in the SU2 repository was used as the reference for marker naming and SU2 export conventions.
