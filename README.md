# Project AETHER

**Aerodynamic Evaluation of Thermal Hazards in Entry Regimes** — multi-objective shape study of a hypersonic re-entry capsule heat shield.

Author: Adithya Kesan Jayakanth (adithya.kesan@icloud.com)
Timeline: technical work June–July 2026, report and technical reviews August 2026.
Project plan: [AETHER_Capstone.md](AETHER_Capstone.md).

## What this repository contains

A reproducible computational study of how nose radius, shoulder radius and rear-body cone angle of an Apollo-like axisymmetric capsule change the drag coefficient and the peak convective heat flux on the heat shield at one fixed hypersonic condition (Mach 10.18, Re_D = 1.1 × 10⁶, cold wall), computed with laminar compressible Navier–Stokes (SU2) on body-fitted structured meshes, validated against two NASA wind-tunnel data sets and assessed with a three-level mesh study.

| Directory | Content |
|---|---|
| `aether/` | Python package: geometry, mesh generation, SU2 configuration, run control, post-processing, mesh-convergence analysis, trade-space analysis, plots |
| `configs/` | operating conditions, SU2 configuration template, sweep table |
| `data/reference/` | NASA reference reports and the digitised/transcribed comparison data |
| `cases/` | one directory per simulation (mesh, configs, logs, histories, solution, summary) |
| `results/` | `results.csv` (every case, including failed ones), trade-space tables, figures |
| `docs/` | geometry, conditions, mesh, validation, logbook, review record, report, slides |
| `scripts/` | installation and figure scripts |
| `tests/` | unit tests |

## Reproducing the study

Requirements: macOS on Apple Silicon (tested on an Apple M4, 10 cores), Homebrew, `uv`, `gh`.

```bash
make env          # Python 3.13 environment, Open MPI 5.0.11, ParaView 6.2.0
make su2          # SU2 v8.5.0 built from source with MPI (see docs/versions.md)
make test         # unit tests
make conditions geometry
make benchmarks   # Benchmark A: Wieting Mach 8.03 cylinder, three meshes
make baseline     # Benchmark B / baseline capsule, three meshes
make domain-check
make sweep        # design-space sweep (configs/sweep.yaml)
make post figures # results/results.csv and all figures
make report       # docs/report/report.pdf
```

Every case directory is self-contained: `mesh.su2`, `stage1.cfg`, `stage2.cfg`, `history_stage*.csv`, `flow_stage2.vtu`, `wall_profile.csv`, `summary.json`, `run_stage*.json` (binary, ranks, wall time, exit code). `results/results.csv` links every number in the report to its case directory.

Exact software versions: [docs/versions.md](docs/versions.md). The SU2 binary is built from the v8.5.0 tag with one source patch (axisymmetric near-axis treatment, SU2 pull request #2715); the reason and the evidence are in [docs/validation.md](docs/validation.md).

## Main documents

- [docs/conditions.md](docs/conditions.md) — operating conditions and gas model limits
- [docs/geometry.md](docs/geometry.md) — capsule family, closure rule, validity rules, Onshape instructions
- [docs/mesh.md](docs/mesh.md) — mesh topology, refinement levels, quality, far-boundary check
- [docs/validation.md](docs/validation.md) — reference comparisons, numerical-scheme investigation, mesh convergence
- [docs/logbook.md](docs/logbook.md) — dated record of decisions, failures and fixes
- [docs/report/report.md](docs/report/report.md) — technical report
- [docs/ai_usage_policy.md](docs/ai_usage_policy.md) — AI usage and research-ownership statement
