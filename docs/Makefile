.DEFAULT_GOAL := all

LATEXMK ?= latexmk
LATEXMK_FLAGS ?= -pdf -interaction=nonstopmode -halt-on-error -file-line-error
REPORT := Basilisk-MPI-CPU-Benchmarks

# latexmk tracks the TeX source, BibTeX file and included figures.
.PHONY: all rebuild clean distclean

all:
	$(LATEXMK) $(LATEXMK_FLAGS) "$(REPORT).tex"

rebuild:
	$(LATEXMK) $(LATEXMK_FLAGS) -g "$(REPORT).tex"

# Keep the compiled report when removing intermediate files.
clean:
	$(LATEXMK) -c "$(REPORT).tex"

distclean:
	$(LATEXMK) -C "$(REPORT).tex"
