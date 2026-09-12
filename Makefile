.DEFAULT_GOAL := all

.PHONY: all rebuild clean distclean

all rebuild clean distclean:
	$(MAKE) -C docs $@
