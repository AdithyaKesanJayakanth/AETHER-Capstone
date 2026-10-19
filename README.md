# AETHER — Aerodynamic Evaluation of Thermal Hazards in Entry Regimes

A student engineering study of how the shape of an Apollo-like re-entry capsule sets the two things its heat shield has to do at once: make drag, and survive the heating that comes with it. Three shape parameters (nose radius, shoulder radius, rear-body cone angle), one fixed hypersonic condition with real wind-tunnel data to be judged against (the Apollo test of NASA TM X-1243: Mach 10.18, Re_D = 1.1 × 10⁶, cold wall), two objectives (maximise C_D, minimise the peak heat flux on the shield), and a selection rule written down before any result. It goes from the question, through a validated laminar Navier–Stokes pipeline on structured meshes drawn from one parameter table, to a ranked trade space with measured uncertainty, and keeps the failures that shaped the method.

> [!IMPORTANT]
> **What the study found.** Drag follows the nose radius and the shoulder radius; the cone half-angle (25–41°) changes drag and peak heating by less than 0.4 %. The heating peak sits at the cap/toroid tangency for every shape with R_n/D ≥ 1. The nondominated set is {sharp shoulder R_s/D = 0.03; the baseline family; R_n/D = 1.0; R_n/D = 1.0 with R_s/D = 0.12}, and the stated rule (lowest peak heating at ≥ 98 % of the baseline drag) selects **R_n/D = 1.0: 5.3 % less peak heating for 1.8 % less drag**, four times the ranking margin measured by mesh refinement.
>
> **What I did not plan.** The first-order scheme converged, on eight of eighteen shapes, to a carbuncle branch with the stagnation pressure 12 % above the pitot limit, and low-CFL retries produced slow transients that passed every monitor. A physical check (stagnation pressure against pitot, plateau against the nose-radius scaling) now decides for every solution, and the fix was in the mesh: cells elongated along the bow shock. See `docs/validation.md` A.5–A.6.

- **Paper**: `docs/report/report.pdf`, source `docs/report/report.md`
- **Slides**: `docs/report/slides.pdf`, source `docs/report/slides.md`
- **Poster** (A0 landscape): `AETHER_Poster.pdf`, source `docs/poster/AETHER_Poster.tex`
- **Video** (two minutes, 1080p, first-person narration): `AETHER_Video.mp4`, script and scene list in `docs/video_script.md`, built by `scripts/video_frames.py`, `scripts/video_narration.py` and `scripts/video_build.py`
- **Code**: the `aether/` package (geometry, meshing, SU2 configuration, run control, post-processing, mesh-convergence and trade-space analysis, plots) and `make all`
- **Every solver case** with its mesh, configuration, log, history and summary under `cases/`; `results/results.csv` links every number in the paper to its case directory
- **Project plan**: [AETHER_Capstone.md](AETHER_Capstone.md) (planned in April; the work ran June–August 2026)

Author: Adithya Kesan Jayakanth (adithya.kesan@icloud.com), Padma Seshadri Bala Bhavan Senior Secondary School, K.K. Nagar, Chennai. Mentor and guide: Mrs. Abhitha Peter, Class 12 Physics teacher.

## What this repository contains

| Directory | Content |
|---|---|
| `aether/` | Python package: geometry, mesh generation, SU2 configuration, run control, post-processing, mesh-convergence analysis, trade-space analysis, plots |
| `configs/` | operating conditions, SU2 configuration template, sweep table |
| `data/reference/` | NASA reference reports and the digitised/transcribed comparison data |
| `cases/` | one directory per simulation (mesh, configs, logs, histories, solution, summary); `cases/variant/` holds families B and C |
| `results/` | `results.csv` (every case, including failed ones), trade-space tables, figures |
| `docs/` | geometry, conditions, mesh, validation, logbook, review record, report, slides, poster, video script, AI-usage policy and log |
| `scripts/` | installation, figure, poster and video scripts |
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
- [docs/report/report.md](docs/report/report.md) — technical report; [docs/report/slides.md](docs/report/slides.md) — slides; [docs/poster/AETHER_Poster.tex](docs/poster/AETHER_Poster.tex) — poster; [docs/video_script.md](docs/video_script.md) — video narration script
- [docs/ai_usage_policy.md](docs/ai_usage_policy.md) — AI usage and research-ownership policy; [docs/ai_use_log.md](docs/ai_use_log.md) — what was actually used, and how it was checked

## Honesty notes

- All results are laminar perfect-gas Navier–Stokes predictions at one wind-tunnel condition. They rank shapes; they do not predict flight heating.
- The absolute heating level is trusted to about 25 % (the gap to the shock-tunnel data of Benchmark A); differences between shapes are trusted to the ranking margins measured by refinement (0.24 % in drag, 1.4 % in peak heating).
- The first mesh family and every retried solver attempt are kept in `cases/` and listed in `results/results.csv`; nothing was removed to make the trade space look cleaner.
- Two shapes (S03, K05) come from the third mesh family; the baseline on that family agrees with the production family to 0.4 % in peak heating, and the offset is added to their margins.
- The Onshape model is a manual step reproduced by the author from the scripted profile; every number in the paper comes from the scripted geometry.

## AI usage

I used an AI assistant as a programming assistant, tutor and reviewer under the policy in [docs/ai_usage_policy.md](docs/ai_usage_policy.md): drafting and debugging the Python pipeline, explaining solver options and numerical behaviour, and reviewing the writing. The research decisions, the physical checks that caught the wrong solutions, the selection rule and the conclusions are mine, and every number in the paper is produced by the code in this repository and checked against reference data or a hand calculation. [docs/ai_use_log.md](docs/ai_use_log.md) lists the assistance actually used and how each output was verified.
