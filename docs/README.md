# Public reports

This directory contains collaborator-facing reports generated from the
repository's verified timing tables and figure assets.

## Resolution and MPI scaling for multiphase flows

- [`Basilisk-MPI-CPU-Benchmarks.tex`](Basilisk-MPI-CPU-Benchmarks.tex) is the
  LaTeX source.
- [`Basilisk-MPI-CPU-Benchmarks.bib`](Basilisk-MPI-CPU-Benchmarks.bib) is the
  BibTeX bibliography.
- [`Basilisk-MPI-CPU-Benchmarks.pdf`](Basilisk-MPI-CPU-Benchmarks.pdf) is the
  compiled shareable report.

The report references canonical plots from [`../figures/`](../figures/). The
plotting scripts remain in [`../postProcess/`](../postProcess/), compact timing
tables stay beside the generated figures, and raw run output remains excluded
from Git. The present source covers the stock kernels, the Marangoni
application series, and three axisymmetric application kernels. It uses these
comparisons to explain how resolution, numerical sensitivity and the useful MPI
rank range should be revisited as a computational research project develops.

Figures 4–6 include four-state temporal sequences from completed simulations.
All report figures use a final width of 166 mm and Computer Modern type sized
to match the captions. Figure reproduction commands and dependencies are
listed in the repository README.

Compile from this directory or the repository root:

```bash
make all
```

This requires `make`, `latexmk` and a LaTeX installation with `pdflatex` and
`bibtex`. The Makefile uses `latexmk` to track changes to the source,
bibliography and included figures and rerun LaTeX until references settle. The
PDF is written beside the source in `docs/`. Figure assets are used as supplied;
the build does not regenerate plots or run simulations.

```bash
make rebuild    # Force LaTeX to rebuild the report
make clean      # Remove intermediate files; keep the PDF
make distclean  # Remove intermediate files and the compiled PDF
```
