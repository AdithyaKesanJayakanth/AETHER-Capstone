# Verification and validation

*Project AETHER. Sections A.2–A.4 record the numerical investigation of 24 June – 2 July 2026 (exploratory runs on the coarse meshes; not part of the final case set). Sections A.1, B and C are filled from `results/results.csv` and the case directories.*

## A. Solver behaviour and settings

### A.1 Benchmark A — Wieting Run 31 cylinder (planar)

Configuration: laminar Navier–Stokes, M = 8.03, p∞ = 855 Pa, T∞ = 124.94 K, isothermal wall 294.44 K, SLAU2 with exact flux Jacobian, stage 1 first order, stage 2 MUSCL + Venkatakrishnan–Wang limiter; three nested polar meshes. Comparison quantities: normalised surface pressure p/P₀ (P₀ = 10.47 psia, the report's stagnation-line pressure) and heat flux q''/Q₀ (Q₀ = 63.49 Btu/ft²·s = 721 kW/m², the report's measured stagnation value) against the transcribed Run 31 table; absolute stagnation heat flux against Fay–Riddell (2-D, perfect gas: 487 kW/m²).

*Results table and figure: filled by `make figures` (results/figures/validation_cylinder.png, cases/benchmarks/wieting_cyl/*/benchmark_cylinder.json).*

### A.2 Choice of the convective scheme (coarse cylinder, exploratory)

All runs: first-order, implicit Euler, from a uniform free stream.

| Scheme | Behaviour at 800–1500 iterations | Wall heat flux | Verdict |
|---|---|---|---|
| AUSM+-up2 | residual stalls at 10⁻²·⁷, bow shock kinked at 40–50° (carbuncle) | not meaningful | rejected |
| AUSM | same | — | rejected |
| Roe, entropy fix 0.1 | same | — | rejected |
| Roe, entropy fix 0.3 | converges to 10⁻⁶ in 490 iterations | stagnation 2.26 MW/m² (3 × experiment): the fix dissipates the boundary layer | rejected |
| JST (central) | converges to 10⁻⁷·⁹ | heating dip at the stagnation line (151 kW/m² at θ = 0, 494 at 13°): carbuncle in a converged solution | rejected |
| SLAU2 + exact Jacobian | residual plateau 10⁻³·⁴, drag and heating stationary to 10⁻⁴ | stagnation 546 kW/m², monotone decrease | **adopted** |
| MSW, SW (flux-vector splitting) | diverge | — | rejected |
| AUSM+M | aborts at start | — | rejected |

On the coarsest cylinder mesh the second-order stage changes the stagnation heat flux from 546 to 535 kW/m² (−2 %) and the drag coefficient from 0.632 to 0.628 (−0.6 %).

**Two steady branches and the start-up procedure (4–7 July).** Refining the mesh from a uniform free-stream start, the first-order SLAU2 solution locked into a carbuncle state on every body (C.1). Two observations resolved this: (i) restarting a carbuncle-free Roe-fix solution with the fix switched off (a source change that scales the fix by a pressure-jump sensor, kept in `tools/aether_su2_patches.diff`) stayed on the clean branch and re-converged to 10⁻¹⁰ — the clean solution is a stable steady state of the operator; (ii) restarting SLAU2 from the converged Roe-fix field converged to the clean branch on the refined cylinder (residual 10⁻⁸·⁷, monotone heating 502 kW/m²) and on the refined capsule (stagnation pressure 25.3 kPa, flat heating 98 → 90 kW/m², shoulder peak 113), where free-stream starts had failed. The Roe-fix solution itself is not usable for heating: its wall-node temperature sits 20–50 K above the imposed value and its heat flux is ×3 (the Roe linearisation with the fix dissipates the entropy wave across the strong density gradient of the boundary layer), which is why SLAU2 is restarted from it. Production procedure: stage 1 Roe (fix 0.3, CFL 0.5 → 10), stage 2 SLAU2 first order (CFL 1 → 30), stage 3 SLAU2 MUSCL for the planar benchmark only.

**CFL.** SU2's adaptive controller started below 1 collapses to its floor during the start-up transient and then crawls; a fixed CFL of 3 from a uniform free stream diverges; a Roe start-up with the cap at 30 can misbehave on the coarsest capsule mesh (stagnation pressure 17 kPa) while a cap of 10 converges. Adopted: adaptive control (factor 0.5 down, 1.2 up), 0.5 → 10 in stage 1 and 1 → 30 in stage 2.

### A.3 Axisymmetric near-axis treatment (SU2 defect and patch)

Test: the validated cylinder mesh and settings run with `AXISYMMETRIC = YES` (a sphere of 38.1 mm radius at the Run 31 condition). Expected: a smooth, monotone heat-flux distribution from the stagnation point; Fay–Riddell (axisymmetric) gives 652 kW/m².

| Solver build | q'' at wall nodes 0°, 1.1°, 2.3°, 3.4°, 5.6°, 9° [kW/m²] | Stagnation pressure, nodes 0–3 [kPa] |
|---|---|---|
| SU2 v8.5.0 release | 504, **154**, 246, 519, 643, 705 | 70.1, **68.5**, 69.7, 69.1 |
| SU2 v7.5.1 release | **70**, 121, 281, 551, 602, 638 | — |
| SU2 v8.5.0 + PR #2715 patch | 848, 829, 794, 770, 752, 708 | 70.8, 70.7, 70.7, 70.5 |

The defect (wrong pressure, temperature and heat flux in the two or three grid columns next to the axis, independent of flux scheme, gradient method, and of moving the symmetry line to y = 10⁻⁶–10⁻⁴ m) is the subject of SU2 issues #1373 and #2438. Pull request #2715 (open since 22 January 2026) replaces the singular 1/r source-term evaluation near the axis by an L'Hôpital-consistent form; its two source-file changes are applied to the v8.5.0 tree (`tools/pr2715.diff`) and the result is the project solver. With the patch the planar and axisymmetric solutions on the same mesh differ only by the physics (stagnation heating ratio sphere/cylinder = 1.55 on the coarse mesh; theory 1.34–1.41), the residual converges to 10⁻⁹·⁶, and the Apollo first-order solution reproduces the measured shape of the heating distribution (Section B).

### A.4 Second-order reconstruction in axisymmetric mode

With the patched solver, MUSCL reconstruction on the Apollo baseline (coarse mesh, truncated domain) does not reach a stationary state:

| Configuration (stage 2, restart from the converged first-order field) | Stagnation pressure range [kPa] (pitot 25.5) | Stagnation heat flux range [kW/m²] |
|---|---|---|
| SLAU2, Venkatakrishnan–Wang 0.05, CFL 1.5 fixed, 4500 it. | 22.8 – 32.7 | 220 – 518 |
| same, limiter frozen after restart | 26.8 – 31.5 | 376 – 518 |
| same, CFL 1.0 | 22.8 – 27.5 | 221 – 350 |
| AUSM+-up2 | 22.7 – 39.6 | 32 – 805 |
| AUSM | 20.8 – 27.6 | −207 – 310 |
| HLLC | 26.7 – 148 | 158 – 5484 |
| **same configuration, AXISYMMETRIC = NO (planar)** | 25.7 – 26.2 | 93 – 106 |
| **first-order SLAU2, axisymmetric** | 25.27 (stationary) | 99.5 (stationary) |

Also tried: Venkatakrishnan (0.05), Venkatakrishnan–Wang 0.3, Barth–Jespersen, van Albada, adaptive CFL, weighted-least-squares reconstruction, Euler-wall axis, coarser and finer shock-normal spacing — none stationary. Since the planar solution is stationary with the same settings and the first-order axisymmetric solution converges, the non-stationarity is attributed to the interaction of SU2's axisymmetric formulation with the reconstruction, not to the physics or the mesh. **Decision:** the axisymmetric production runs use first-order SLAU2. The discretisation error is quantified by the three-level mesh study (observed order and Richardson extrapolation, Section C) and the first/second-order difference is reported on the cylinder benchmark (A.1), where both are stable. This is a stated limitation of the study.

### A.5 Heat-flux evaluation and convergence criteria

- Wall heat flux and pressure are taken at the wall nodes of the volume solution (`aether/vtkio.py`), cross-checked against −k ΔT/Δn from the first cell (agreement within 3 %). SU2's history field MAXIMUM_HEATFLUX is not the nodal maximum (serial check: 723 vs 546 kW/m²) and is used only as a stationarity monitor.
- Sign convention: SU2's `Heat_Flux` is positive into the wall; negative values occur only on the cold expanded flow over the cone where the 300 K wall heats the gas.
- A case is "converged" when (i) the Cauchy criterion of SU2 on drag and the heat-flux monitor (relative change < 2 × 10⁻⁵ over 500 iterations) stops the run or the iteration limit is reached, and (ii) the post-processor finds drag and the heat-flux monitor flat to 0.1 % over the last 500 iterations and the density residual reduced by at least one order. Cases failing (ii) are kept in `results.csv` with status `not_converged`.

## B. Benchmark B — Apollo at α = 0 (axisymmetric)

Configuration: main condition (docs/conditions.md), baseline geometry, first-order SLAU2 (A.4), three nested meshes, truncated domain (docs/mesh.md). Comparisons: p/p_t2 vs S/R against TM X-1243 Fig. 3a; q''/q''_t vs S/R against Fig. 8a (range of data), with q''_t the computed stagnation value; stagnation pressure against the Rayleigh pitot value; stagnation heat flux against Fay–Riddell; drag coefficient against the integral of the measured forebody pressure and against modified Newtonian theory.

*Results: filled by `make figures` (results/figures/validation_apollo.png, cases/baseline/*/benchmark_apollo.json).*

## C. Mesh convergence and domain check

### C.1 Refinement of the shock region (exploratory, 4 July 2026)

Refining every spacing by 1.5 from the base level re-triggers the stagnation-line instability of the first-order solution, independently of the flux function:

| Case (first order, patched solver) | Result at the stagnation line |
|---|---|
| Cylinder, all spacings ÷ 1.5, SLAU2 (two stages) | heat flux 932 kW/m² at θ = 0 against 460–470 at 9–18°, residual plateau 10⁻³·⁸ |
| Cylinder, tangential ÷ 1.5 only, SLAU2 | 754 kW/m² at θ = 0 decaying to 609 at 6° (bump of +24 %) |
| Cylinder, boundary layer ÷ 1.5 only, SLAU2 | 546 → 532 → 521 → 514 … kW/m² (smooth, Lees-like) |
| Cylinder, all spacings ÷ 1.5, AUSM+-up2 (Kp 0.25) | 1134 kW/m² at θ = 0, 464 at 9° |
| Cylinder, same, AUSM+-up2 with Kp = 1.0 and 3.0 | diverge |
| Capsule, all spacings ÷ 1.5, SLAU2 | stagnation pressure 29–32 kPa (pitot 25.5), heating spike 360–560 kW/m² |
| Capsule, same, Roe with entropy fix 0.05 | stagnation pressure 51 kPa |
| Capsule, boundary layer ÷ 1.5 only, SLAU2 | stagnation pressure 25.4 kPa; near-axis bump +40 % within s/R < 0.05; plateau (s/R = 0.3) 93 vs 94 kW/m², shoulder peak 113 vs 115 |
| Capsule, boundary layer ÷ 2.25 only, SLAU2 (gentle start) | converged; see results table |

The boundary-layer-only family was adopted provisionally on 5 July, then abandoned on 7 July when the base-level capsule itself locked into the carbuncle branch after a change of the far-field stretching only: the branch selection is a property of the start-up transient, not of the mesh (A.2). With the Roe-fix start-up the fully refined levels converge to the clean branch (cylinder 502 and 520 kW/m² at ÷1.5 and ÷2.25; capsule 25.3 kPa, 98 kW/m²), and the production family refines every spacing (docs/mesh.md). The coarsest 1.2 mm capsule mesh still locks into the carbuncle branch even with the start-up procedure and is not used; the family starts at 0.8 mm.

### C.2 Boundary-layer refinement, Richardson extrapolation and domain checks

Three nested levels (r = 1.5 in every spacing), Richardson extrapolation and GCI (Celik et al. 2008) separately for C_D and the heating quantities; far-boundary check at 3.0 D / 7.0 D. The acceptance tolerance used in the trade-space analysis is the larger of the coarse-level GCI and the far-boundary sensitivity for each objective: two designs are only called different if they differ by more than it.

*Results: filled from results/results.csv and results/uncertainty.json.*
