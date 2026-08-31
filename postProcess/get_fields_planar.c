/**
# Regular-grid fields from a planar dump

Restores `f`, `u` and, when present, the activity concentration `cL`
by name, then interpolates them onto a regular $n_x \times n_y$ grid
over `[xmin,xmax] x [ymin,ymax]`. Extra dump fields are ignored.
Marangoni-interact dumps have no `cL`; that column is then zero.

Use this helper for planar `activity-drop` and `marangoni-interact`
snapshots. The axisymmetric Al Saud extractor remains `get_fields.c`.

Usage: `get_fields_planar snapshot-file xmin xmax ymin ymax ny`

Columns: `x y f ux uy cL`
*/
#include "utils.h"
#include "output.h"
#include "fractions.h"

scalar f[];
vector u[];
scalar cL[];

int main (int argc, char const * argv[])
{
  if (argc < 7) {
    fprintf (stderr,
	     "usage: %s snapshot-file xmin xmax ymin ymax ny\n", argv[0]);
    return 1;
  }
  double xmin = atof (argv[2]), xmax = atof (argv[3]);
  double ymin = atof (argv[4]), ymax = atof (argv[5]);
  int ny = atoi (argv[6]);
  if (!isfinite (xmin) || !isfinite (xmax) || xmax <= xmin ||
      !isfinite (ymin) || !isfinite (ymax) || ymax <= ymin || ny <= 0) {
    fprintf (stderr, "%s: require finite bounds and ny > 0\n", argv[0]);
    return 1;
  }
  if (!restore (file = argv[1])) {
    fprintf (stderr, "%s: cannot restore '%s'\n", argv[0], argv[1]);
    return 1;
  }
  f.prolongation = fraction_refine;

  double dy = (ymax - ymin)/ny;
  int nx = (int) ((xmax - xmin)/dy);
  if (nx < 1)
    nx = 1;
  double dx = (xmax - xmin)/nx;

  fprintf (stdout, "# nx %d ny %d\n", nx, ny);
  for (int i = 0; i < nx; i++) {
    double x = xmin + dx*(i + 0.5);
    for (int j = 0; j < ny; j++) {
      double y = ymin + dy*(j + 0.5);
      fprintf (stdout, "%g %g %g %g %g %g\n",
	       x, y,
	       interpolate (f, x, y),
	       interpolate (u.x, x, y),
	       interpolate (u.y, x, y),
	       interpolate (cL, x, y));
    }
  }
  return 0;
}
