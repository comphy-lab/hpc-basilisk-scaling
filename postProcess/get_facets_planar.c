/**
# Interface facets from a planar dump

Restores `f` by name and writes VOF facets (`output_facets()`) to
stdout. Use with planar `activity-drop` and `marangoni-interact`
snapshots. The axisymmetric Al Saud extractor remains `get_facets.c`.

Usage: `get_facets_planar snapshot-file`
*/
#include "utils.h"
#include "output.h"
#include "fractions.h"

scalar f[];

int main (int argc, char const * argv[])
{
  if (argc < 2) {
    fprintf (stderr, "usage: %s snapshot-file\n", argv[0]);
    return 1;
  }
  if (!restore (file = argv[1])) {
    fprintf (stderr, "%s: cannot restore '%s'\n", argv[0], argv[1]);
    return 1;
  }
  f.prolongation = fraction_refine;
  output_facets (f, stdout);
  return 0;
}
