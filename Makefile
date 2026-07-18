# Project AETHER - reproducible pipeline
# Each target is idempotent: finished cases (summary.json present) are skipped with --skip-done.
PY := .venv/bin/python
NPROC ?= 8
FAMILY ?= t15        # production mesh family (B); t20 = family C; empty = family A
VAR := $(if $(FAMILY),--mesh-variant $(FAMILY),)

.PHONY: env su2 test conditions geometry benchmarks baseline domain-check sweep supplement refine post uncertainty figures tables fields report all clean-cases

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

baseline:          ## Benchmark B / baseline capsule on coarse/medium/fine (family $(FAMILY))
	$(PY) -m aether baseline $(VAR) --nproc $(NPROC) --skip-done

domain-check:      ## baseline (medium) with a larger far boundary
	$(PY) -m aether domain-check $(VAR) --nproc $(NPROC) --skip-done

sweep:             ## design-space sweep from configs/sweep.yaml (resumable)
	$(PY) -m aether sweep $(VAR) --nproc $(NPROC) --skip-done

supplement:        ## family C for the shapes that stay on the carbuncle branch on family B, with its baseline controls
	AETHER_MAX_RETRIES=0 $(PY) -m aether sweep --mesh-variant t20 --only B00 S03 K05 --nproc $(NPROC) --skip-done
	AETHER_MAX_RETRIES=0 $(PY) -m aether baseline --mesh-variant t20 --levels fine --nproc $(NPROC) --skip-done

refine:            ## finalists at the fine level (ranking stability)
	AETHER_MAX_RETRIES=0 $(PY) -m aether refine $(VAR) --ids N10 C41 K03 --levels fine --nproc $(NPROC) --skip-done
	AETHER_MAX_RETRIES=0 $(PY) -m aether refine --mesh-variant t20 --ids S03 --levels fine --nproc $(NPROC) --skip-done

post:              ## collect every case into results/results.csv
	$(PY) -m aether post

uncertainty:       ## GCI, domain check, ranking margins -> results/uncertainty.json, docs/mesh_convergence.md
	$(PY) -m aether uncertainty

figures:           ## all figures into results/figures
	$(PY) -m aether figures

tables:            ## results/tables.md
	$(PY) -m aether tables

fields:            ## ParaView field figures (pvpython)
	$(PY) -m aether fields

report:            ## docs/report/report.pdf from docs/report/report.md (pandoc)
	bash scripts/build_report.sh

all: test conditions geometry benchmarks baseline domain-check sweep supplement refine post uncertainty figures tables fields

clean-cases:       ## remove solver output but keep configs and meshes
	find cases -name '*.vtu' -delete -o -name 'restart_*.dat' -delete -o -name '*.log' -delete
