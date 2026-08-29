/**
# Regular-grid fields from a Marangoni snapshot

Restores one `dump()` file from `marangoni-scale.c` and interpolates
`f`, `d`, `sigmaf`, `u.x` and `u.y` onto a regular `nx` x `ny` grid
over `[xmin,xmax] x [ymin,ymax]`. Also reports the drop centre of mass
and bulk velocity (the \(1-f\) phase) as a comment, so a later plot
can shift into the drop frame.

Usage: `get_fields snapshot-file xmin xmax ymin ymax ny`

Columns: `x y f d sigmaf ux uy`
*/
#include "axi.h"
#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"
#include "fractions.h"

scalar sigmaf[];

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

  d.sigmaf = sigmaf;
  if (!restore (file = argv[1])) {
    fprintf (stderr, "%s: cannot restore '%s'\n", argv[0], argv[1]);
    return 1;
  }
  f.prolongation = fraction_refine;

  double xb = 0., vb = 0., sb = 0.;
  foreach (reduction(+:xb) reduction(+:vb) reduction(+:sb)) {
    double dv = (1. - f[])*dv();
    vb += u.x[]*dv;
    xb += x*dv;
    sb += dv;
  }

  double dy = (ymax - ymin)/ny;
  int nx = (int) ((xmax - xmin)/dy);
  if (nx < 1)
    nx = 1;
  double dx = (xmax - xmin)/nx;

  fprintf (stdout, "# nx %d ny %d\n", nx, ny);
  fprintf (stdout, "# xb %g vb %g sb %g\n",
	   sb > 0. ? xb/sb : 0., sb > 0. ? vb/sb : 0., sb);

  for (int i = 0; i < nx; i++) {
    double x = xmin + dx*(i + 0.5);
    for (int j = 0; j < ny; j++) {
      double y = ymin + dy*(j + 0.5);
      fprintf (stdout, "%g %g %g %g %g %g %g\n",
	       x, y,
	       interpolate (f, x, y),
	       interpolate (d, x, y),
	       interpolate (sigmaf, x, y),
	       interpolate (u.x, x, y),
	       interpolate (u.y, x, y));
    }
  }
  return 0;
}
