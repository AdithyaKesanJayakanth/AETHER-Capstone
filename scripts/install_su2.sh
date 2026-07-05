#!/usr/bin/env bash
# Build SU2 v8.5.0 "Harrier" from source (native arm64, Open MPI) into tools/su2-native,
# and optionally the official x86_64 binary (runs under Rosetta 2, serial) into tools/su2-rosetta.
#
#   scripts/install_su2.sh            native build (default)
#   scripts/install_su2.sh rosetta    download the official macOS binary instead
#
# The near-axis fix for axisymmetric flows (SU2 pull request #2715) is applied on top of
# v8.5.0 when the file tools/pr2715.diff is present; see docs/validation.md section A.3 for
# why it is needed and what it changes.
set -euo pipefail
cd "$(dirname "$0")/.."
TAG=v8.5.0

if [[ "${1:-native}" == "rosetta" ]]; then
  mkdir -p tools/su2-rosetta && cd tools/su2-rosetta
  gh release download "$TAG" --repo su2code/SU2 --pattern "SU2-${TAG}-macos64.zip" --clobber
  unzip -oq "SU2-${TAG}-macos64.zip" && unzip -oq macos64.zip && rm -f "SU2-${TAG}-macos64.zip" macos64.zip
  ./bin/SU2_CFD --help | head -1
  exit 0
fi

command -v mpicxx >/dev/null || { echo "Open MPI not found; run scripts/install_tools.sh first"; exit 1; }
[[ -d tools/src ]] || git clone --depth 1 --branch "$TAG" https://github.com/su2code/SU2.git tools/src
cd tools/src
if [[ -f ../pr2715.diff ]] && ! git apply --reverse --check --include='SU2_CFD/*' ../pr2715.diff 2>/dev/null; then
  git apply --include='SU2_CFD/*' ../pr2715.diff && echo "applied PR 2715 near-axis patch"
fi
./meson.py setup build -Dwith-mpi=enabled -Denable-pywrapper=false --prefix="$(pwd)/../su2-native"
./ninja -C build install
../su2-native/bin/SU2_CFD --help | head -1
