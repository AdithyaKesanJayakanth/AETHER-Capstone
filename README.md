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
| `cases/` | one directory per simulation (mesh, configs, logs, histories, solution, summary); `cases/variant/` holds families B and C |
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

The production results are computed on mesh family B (`--mesh-variant t15`: cells elongated along the bow shock), with family C (`--mesh-variant t20`) for the two shapes that stay on the carbuncle branch on B, and the first family A kept as a cross-check (`docs/mesh.md`, `docs/validation.md` A.6). The exact command sequence that produced `results/` is:

```bash
python -m aether baseline     --mesh-variant t15            # B00 coarse/medium/fine
python -m aether domain-check --mesh-variant t15
python -m aether sweep        --mesh-variant t15            # 18 valid shapes + X02 + rejections
AETHER_MAX_RETRIES=0 python -m aether sweep --mesh-variant t20 --only B00 S03 K05
AETHER_MAX_RETRIES=0 python -m aether refine --mesh-variant t15 --ids N10 C41 K03 --levels fine
AETHER_MAX_RETRIES=0 python -m aether refine --mesh-variant t20 --ids S03 --levels fine
AETHER_MAX_RETRIES=0 python -m aether baseline --mesh-variant t20 --levels fine
python -m aether post && python -m aether uncertainty && python -m aether figures && python -m aether tables && python -m aether fields
```

`python -m aether post` tags every case with its family (A/B/C), base id and role; the analysis commands take `--family` (default B) and supplement family B with family C where B has no converged result.

Every case directory is self-contained: `mesh.su2`, `stage1.cfg`, `stage2.cfg`, `history_stage*.csv`, `flow_stage2.vtu`, `wall_profile.csv`, `summary.json`, `run_stage*.json` (binary, ranks, wall time, exit code). `results/results.csv` links every number in the report to its case directory.

Exact software versions: [docs/versions.md](docs/versions.md). The SU2 binary is built from the v8.5.0 tag with the source changes of SU2 pull request #2715 (axisymmetric near-axis treatment) applied, plus two environment-variable test hooks that are inactive in production (`tools/aether_su2_patches.diff`); the reasons and the evidence are in [docs/validation.md](docs/validation.md). Each case runs as a Roe-fix start-up stage followed by a SLAU2 first-order analysis stage (and a second-order stage for the planar benchmark), with a physical-branch check and automatic retries described there.

## Main documents

- [docs/conditions.md](docs/conditions.md) — operating conditions and gas model limits
- [docs/geometry.md](docs/geometry.md) — capsule family, closure rule, validity rules, Onshape instructions
- [docs/mesh.md](docs/mesh.md) — mesh topology, refinement levels, quality, far-boundary check
- [docs/validation.md](docs/validation.md) — reference comparisons, numerical-scheme investigation, mesh convergence
- [docs/logbook.md](docs/logbook.md) — dated record of decisions, failures and fixes
- [docs/report/report.md](docs/report/report.md) — technical report
- [docs/ai_usage_policy.md](docs/ai_usage_policy.md) — AI usage and research-ownership statement
