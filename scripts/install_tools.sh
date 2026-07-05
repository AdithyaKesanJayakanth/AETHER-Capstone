#!/usr/bin/env bash
# Python environment, Open MPI and ParaView for Project AETHER (macOS, Apple Silicon).
# Versions are pinned in pyproject.toml / uv.lock; see docs/versions.md for the record of what was used.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v brew >/dev/null || { echo "Homebrew is required: https://brew.sh"; exit 1; }
command -v uv >/dev/null || brew install uv

brew list open-mpi >/dev/null 2>&1 || brew install open-mpi        # 5.0.11 used
brew list --cask paraview >/dev/null 2>&1 || brew install --cask paraview   # 6.2.0 used

uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -e .
.venv/bin/python -c "import gmsh, numpy, scipy, matplotlib, pandas, vtk; print('python environment ok')"
echo "done. Activate with: source .venv/bin/activate"
