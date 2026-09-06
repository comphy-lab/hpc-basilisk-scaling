/**
# Drop-impact illustration extractor

Restores an axisymmetric Newtonian drop-impact snapshot and samples the liquid
fraction and velocity components on a regular $(z,r)$ grid. Basilisk uses
`x` for the axial coordinate normal to the substrate and `y` for the radial
coordinate. Interface facets are written to standard error using the geometric
VOF reconstruction.

Usage: `extract_drop_image snapshot zmin zmax rmax nr`

Standard-output columns: `z r f uz ur speed`

## Provenance

The field list and boundary conditions follow the archived Newtonian
drop-impact `getData.c` and `getFacet.c` post-processing tools. The liquid is
`f = 1`; the substrate is the `left` boundary and the symmetry axis is the
`bottom` boundary under `axi.h`.

## Author

Vatsal Sanjay and the Computational Multiphase Physics Lab
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#include "fractions.h"

scalar f[];

u.t[left] = dirichlet (0.0);
f[left] = dirichlet (0.0);
u.n[right] = neumann (0.0);
p[right] = dirichlet (0.0);
u.n[top] = neumann (0.0);
p[top] = dirichlet (0.0);

int main (int argc, char const * argv[])
{
  if (argc != 6) {
    fprintf (stderr,
             "usage: %s snapshot zmin zmax rmax nr\n", argv[0]);
    return 1;
  }

  const char * snapshot = argv[1];
  double zmin = atof (argv[2]);
  double zmax = atof (argv[3]);
  double rmax = atof (argv[4]);
  int nr = atoi (argv[5]);
  if (!isfinite (zmin) || !isfinite (zmax) || !isfinite (rmax) ||
      zmin < 0.0 || zmax <= zmin || rmax <= 0.0 || nr <= 0) {
    fprintf (stderr, "%s: invalid bounds or radial resolution\n", argv[0]);
    return 1;
  }

  if (!restore (file = snapshot)) {
    fprintf (stderr, "%s: cannot restore '%s'\n", argv[0], snapshot);
    return 1;
  }
  f.prolongation = fraction_refine;
  boundary (all);

  output_facets (f, stderr);

  double dr = rmax/nr;
  int nz = (int) ((zmax - zmin)/dr);
  if (nz <= 0) {
    fprintf (stderr, "%s: axial resolution is empty\n", argv[0]);
    return 1;
  }

  fprintf (stdout, "# nz %d nr %d\n", nz, nr);
  fprintf (stdout, "# z r f uz ur speed\n");
  for (int iz = 0; iz < nz; iz++) {
    double z = zmin + (iz + 0.5)*dr;
    for (int ir = 0; ir < nr; ir++) {
      double r = (ir + 0.5)*dr;
      double fraction = interpolate (f, z, r);
      double uz = interpolate (u.x, z, r);
      double ur = interpolate (u.y, z, r);
      fprintf (stdout, "%.12g %.12g %.12g %.12g %.12g %.12g\n",
               z, r, fraction, uz, ur, sqrt (sq(uz) + sq(ur)));
    }
  }
  return 0;
}
