#!/usr/bin/env bash
# Render docs/report/report.md to PDF with pandoc + tectonic (both from Homebrew).
set -euo pipefail
cd "$(dirname "$0")/.."
command -v pandoc >/dev/null || brew install pandoc
command -v tectonic >/dev/null || brew install tectonic
cd docs/report
pandoc -f markdown-smart report.md -o report.pdf --pdf-engine=tectonic --resource-path=.:../..:../../results/figures \
  -V geometry:margin=2.2cm -V fontsize=11pt -V colorlinks=true -V mainfont="Times New Roman" -V mathfont="STIX Two Math" --number-sections --toc
pandoc -f markdown-smart slides.md -t beamer -o slides.pdf --pdf-engine=tectonic --resource-path=.:../..:../../results/figures \
  -V mainfont="Times New Roman" -V theme=metropolis 2>/dev/null || \
pandoc -f markdown-smart slides.md -t beamer -o slides.pdf --pdf-engine=tectonic --resource-path=.:../..:../../results/figures -V mainfont="Times New Roman"
cd ../poster && tectonic AETHER_Poster.tex && mv AETHER_Poster.pdf ../../AETHER_Poster.pdf
echo "wrote docs/report/report.pdf, docs/report/slides.pdf and AETHER_Poster.pdf"
