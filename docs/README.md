# Public reports

This directory contains collaborator-facing reports generated from the
repository's verified timing tables and figure assets.

## Basilisk MPI scaling for multiphase flows

- [`Basilisk-MPI-CPU-Benchmarks.tex`](Basilisk-MPI-CPU-Benchmarks.tex) is the
  complete, single-file LaTeX source.
- [`Basilisk-MPI-CPU-Benchmarks.pdf`](Basilisk-MPI-CPU-Benchmarks.pdf) is the
  compiled shareable report.

The report references canonical plots from [`../figures/`](../figures/). The
plotting scripts remain in [`../postProcess/`](../postProcess/), compact timing
tables stay beside the generated figures, and raw run output remains excluded
from Git. The present source covers the stock kernels, the Marangoni
application series, and three axisymmetric uniform-grid application kernels.

Figures 4–6 include four-state temporal sequences from completed simulations.
All report figures use a final width of 166 mm and Computer Modern type sized
to match the captions. Figure reproduction commands and dependencies are
listed in the repository README.

Compile from this directory, running LaTeX twice to resolve references:

```bash
pdflatex -halt-on-error -interaction=nonstopmode Basilisk-MPI-CPU-Benchmarks.tex
pdflatex -halt-on-error -interaction=nonstopmode Basilisk-MPI-CPU-Benchmarks.tex
```
