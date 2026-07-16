# Mesh generation

*Project AETHER — mesh definition frozen 19 June 2026 after the numerical investigation recorded in docs/validation.md and docs/logbook.md; the production family (B) was fixed on 16 July 2026 after the sweep on the first family (A) showed a mesh-dependent carbuncle branch (see "Two mesh families" below).*

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
| Stretched cells to the far boundary | 36 (ratio ≈ 1.10) | 20 |
| Wall spacing: nose cap / shoulder / cone | family A: 0.8 / 0.3 / 1.1 mm; family B: 1.2 / 0.3 / 1.1 mm | 0.75° (0.5 mm) |
| Cells (baseline geometry, coarse / medium / fine) | family A: 49 056 / 109 500 / 246 375; family B: 43 680 / 97 500 / 219 375 | 23 380 / 52 290 / 117 180 |

The estimated stagnation-region thermal layer is 0.4 mm thick on the capsule and 0.12 mm on the cylinder (Fay–Riddell velocity gradient); the base first-cell heights place about 25 cells inside it.

**Refinement family (coarse / medium / fine).** Every spacing is divided by 1.5 per level (first cell 3.0 → 2.0 → 1.33 µm on the capsule; the growth ratio is reduced so that the number of cells across a fixed layer thickness scales by the same factor: 1.15 → 1.10 → 1.067); the cell count grows by about 2.25 per level. This is a nested family with refinement ratio r = 1.5, as the Richardson/GCI analysis in `aether/convergence.py` assumes. The design sweep is run on the medium level (the coarse level still carries a near-axis residue, docs/validation.md A.5); the baseline is run on all three levels and the finalists on medium and fine.

**Two mesh families.** Family A has isotropic cells in the shock region (the cap wall spacing equals the shock-normal spacing: 0.8 mm at the coarse level, 0.53 mm at the medium level). On this family 10 of the 18 valid sweep shapes converged to the physical branch at the first attempt, while 8 (S03, S08, N10, K01–K05) converged, from any start-up including a converged neighbouring solution interpolated onto their mesh, to the carbuncle branch only (docs/validation.md A.5, A.6). The carbuncle is the shock-aligned instability of upwind fluxes and is strongest when the cells along the shock are as small as the cells across it; the textbook remedy is to elongate the cells along the shock. Family B therefore uses a cap wall spacing 1.5 × the shock-normal spacing (1.2 mm at the coarse level, 0.8 mm at the medium level; shoulder, cone, boundary-layer and normal spacings unchanged), giving an aspect ratio of about 1.5 in the shock region ahead of the cap. The two families are generated by the same code (`MESH_VARIANTS["t15"]` in `aether/__main__.py`, directories `cases/variant/*_t15`) and differ in nothing else. Family B is the production family: the sweep, the three baseline levels, the far-boundary check and the finalist refinements are reported on it; the family-A results are kept as an independent cross-check for every shape that converged on both (results/tables.md).

**Start-up procedure.** The first-order SLAU2 solution of this problem has two steady branches on every level tested: the physical one and a carbuncle branch (stagnation pressure above the pitot value, heating spike at the stagnation line). Which branch a run converges to depends on the start-up transient, not on the mesh quality: a coarser 1.2 mm family that is clean from a uniform free-stream start on one far-field stretching locks into the carbuncle branch on another. The production procedure therefore establishes the field with a Roe flux and a large entropy fix (carbuncle-free, strongly convergent) and restarts SLAU2 from it (docs/validation.md A.2). The procedure is necessary but not sufficient: on family A it reaches the physical branch for the baseline at every level and for 10 of 18 sweep shapes, and family B was introduced for the rest (above). A post-processing check (stagnation pressure against the pitot value) decides, for every case, which branch a converged solution is on.

## Quality metrics (written to `mesh_report.json` of every case)

Signed cell area (no inverted cell allowed), minimum and maximum interior angle, maximum aspect ratio, first-cell height range, cell and point counts. Baseline coarse level: minimum angle 45°, maximum angle 135°, maximum aspect ratio ≈ 270 (boundary-layer cells; expected and intended), no inverted cells. Every sweep case must pass the same checks before the solver is called; a failing mesh is recorded as an invalid case.

## Far-boundary check

`cases/domain_check/base_far` (family A) and `cases/variant/B00_base_far_t15` (family B) repeat the baseline at the medium level with the far boundary moved from 2.0 D to 3.0 D at the nose and from 4.5 D to 7.0 D downstream. The change in C_D and q''_max is reported in docs/validation.md and must be smaller than the mesh uncertainty for the chosen domain to be accepted.

## Gmsh

Gmsh 4.15.2 is installed in the environment and was evaluated for an unstructured alternative (triangles with a quadrilateral boundary-layer field). It was not adopted because (i) laminar hypersonic heat flux is set by the wall-normal temperature gradient across a sub-millimetre layer, for which wall-orthogonal, smoothly growing quadrilaterals are the standard and most reliable discretisation; (ii) nested refinement by an exact factor is straightforward for the structured generator and is what the Richardson analysis assumes; (iii) the structured generator produces every candidate shape from the parameter table with no manual intervention. The SU2 `navierstokes/sphere` test case's Gmsh script in the SU2 repository was used as the reference for marker naming and SU2 export conventions.
