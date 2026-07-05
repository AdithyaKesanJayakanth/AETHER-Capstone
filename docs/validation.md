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

The residual plateau of SLAU2 at a strong captured shock is the known behaviour of upwind schemes with limiters/pressure sensors; convergence is therefore judged on the stationarity of the integrated quantities (drag, wall heat flux), with the residual drop recorded. On the coarse cylinder the second-order stage changes the stagnation heat flux from 546 to 535 kW/m² (−2 %) and the drag coefficient from 0.632 to 0.628 (−0.6 %).

**CFL.** SU2's adaptive controller started below 1 collapses to its floor during the start-up transient and then crawls; a fixed CFL of 3 from a uniform free stream diverges. Adopted: adaptive control between 1 and 50 (factor 0.5 down, 1.3 up) for the first-order stage, which reaches CFL 50 once the shock is established.

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

Three nested meshes (r = 1.5), Richardson extrapolation and GCI (Celik et al. 2008) separately for C_D and q''_max,shield; far-boundary check at 3.0 D / 7.0 D. The acceptance tolerance used in the trade-space analysis is the GCI of the medium mesh for each objective: two designs are only called different if they differ by more than it.

*Results: filled from results/results.csv and results/uncertainty.json.*
