#!/usr/bin/env bash
# Render docs/report/report.md to PDF with pandoc + tectonic (both from Homebrew).
set -euo pipefail
cd "$(dirname "$0")/.."
command -v pandoc >/dev/null || brew install pandoc
command -v tectonic >/dev/null || brew install tectonic
cd docs/report
pandoc report.md -o report.pdf --pdf-engine=tectonic --resource-path=.:../..:../../results/figures \
  -V geometry:margin=2.2cm -V fontsize=11pt -V colorlinks=true --number-sections --toc
echo "wrote docs/report/report.pdf"
