/**
# Interface facets from a Marangoni snapshot

Restores one `dump()` file from `marangoni-scale.c` and writes the VOF
interface of `f` as line segments (`output_facets()`) to stdout.

The include list must match the solver so `restore()` sees the same
fields.

Usage: `get_facets snapshot-file`
*/
#include "axi.h"
#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"
#include "fractions.h"

scalar sigmaf[];

int main (int argc, char const * argv[])
{
  if (argc < 2) {
    fprintf (stderr, "usage: %s snapshot-file\n", argv[0]);
    return 1;
  }
  d.sigmaf = sigmaf;
  if (!restore (file = argv[1])) {
    fprintf (stderr, "%s: cannot restore '%s'\n", argv[0], argv[1]);
    return 1;
  }
  f.prolongation = fraction_refine;
  output_facets (f, stdout);
  return 0;
}
