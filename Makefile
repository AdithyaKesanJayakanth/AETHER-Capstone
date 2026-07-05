# Project AETHER - reproducible pipeline
# Each target is idempotent: finished cases (summary.json present) are skipped with --skip-done.
PY := .venv/bin/python
NPROC ?= 8

.PHONY: env su2 test conditions geometry benchmarks baseline domain-check sweep post figures report all clean-cases

env:               ## Python environment, Open MPI, ParaView
	bash scripts/install_tools.sh

su2:               ## build SU2 v8.5.0 (native arm64, MPI) with the near-axis patch
	bash scripts/install_su2.sh

test:              ## unit tests (geometry, configuration, post-processing)
	$(PY) -m pytest -q tests

conditions:        ## docs/conditions.md from configs/conditions.yaml
	$(PY) -m aether conditions

geometry:          ## baseline profile, labelled sketch, parameter table
	$(PY) -m aether geometry

benchmarks:        ## Benchmark A: Wieting cylinder on coarse/medium/fine
	$(PY) -m aether benchmark-cyl --nproc $(NPROC) --skip-done

baseline:          ## Benchmark B / baseline capsule on coarse/medium/fine
	$(PY) -m aether baseline --nproc $(NPROC) --skip-done

domain-check:      ## baseline (medium) with a larger far boundary
	$(PY) -m aether domain-check --nproc $(NPROC) --skip-done

sweep:             ## design-space sweep from configs/sweep.yaml (resumable)
	$(PY) -m aether sweep --nproc $(NPROC) --skip-done

post:              ## collect every case into results/results.csv
	$(PY) -m aether post

figures:           ## all figures into results/figures
	$(PY) -m aether figures

report:            ## docs/report/report.pdf from docs/report/report.md (pandoc)
	bash scripts/build_report.sh

all: test conditions geometry benchmarks baseline domain-check sweep post figures

clean-cases:       ## remove solver output but keep configs and meshes
	find cases -name '*.vtu' -delete -o -name 'restart_*.dat' -delete -o -name '*.log' -delete
