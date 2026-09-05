/**
# Uniform-grid jumping-drops serial init (cluster)

Serial first phase from
[comphy-lab/Jumping-Drops](https://github.com/comphy-lab/Jumping-Drops)
`jumpingDrops_init.c` at `f4ea474`. Reads `InitialCondition.stl` with
Basilisk `distance.h` (not MPI-safe), fills a uniform octree, dumps
`dumpInit`, and stops. Do not compile with `-D_MPI=1`. Do not include
`jumpingDrops_common.h`: that header always registers `adapt_wavelet`.

Usage:

~~~
./jumping-uniform-init LEVEL
~~~

Default LEVEL 7 is $128^3$ cells on $L_0=4$. Place `InitialCondition.stl`
in the working directory. Gravity $G_y=-\mathrm{Bo}$ must match the
MPI continuation.
*/

#include "grid/octree.h"
#include "navier-stokes/centered.h"
#define FILTERED 1
#include "two-phase.h"
#include "navier-stokes/conserving.h"
#include "tension.h"
#include "distance.h"
#include "reduced.h"

int LEVEL = 7;
double Oh = 0.005, Bo = 0.001;
double tmax = 1.;

#define Rho21 (1.00e-3)
#define Mu21 (1.00e-2)

u.t[bottom] = dirichlet(0.);
u.r[bottom] = dirichlet(0.);
f[bottom] = dirichlet(0.);

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (LEVEL < 5 || LEVEL > 8) {
    fprintf (stderr, "jumping-uniform-init: LEVEL=%d out of range [5,8]\n",
	     LEVEL);
    exit (1);
  }

  L0 = 4.;
  init_grid (1 << LEVEL);
  N = 1 << LEVEL;

  rho1 = 1.0;
  mu1 = Oh;
  rho2 = Rho21;
  mu2 = Mu21*Oh;
  f.sigma = 1.0;
  G.y = -Bo;

  fprintf (stderr,
	   "jumping-uniform-init LEVEL=%d L0=%g Oh=%g Bo=%g\n",
	   LEVEL, L0, Oh, Bo);

  run();
}

event init (t = 0)
{
  FILE * fp = fopen ("InitialCondition.stl", "r");
  if (!fp) {
    fprintf (stderr, "jumping-uniform-init: missing InitialCondition.stl\n");
    exit (1);
  }
  coord * p = input_stl (fp);
  fclose (fp);

  coord min, max;
  bounding_box (p, &min, &max);
  fprintf (stderr, "STL bbox x[%g,%g] y[%g,%g] z[%g,%g]\n",
	   min.x, max.x, min.y, max.y, min.z, max.z);

  origin (0., -1. - L0/pow(2, LEVEL), (min.z + max.z)/2.);

  scalar d[];
  distance (d, p);

  vertex scalar phi[];
  foreach_vertex()
    phi[] = (d[] + d[-1] + d[0,-1] + d[-1,-1] +
	     d[0,0,-1] + d[-1,0,-1] + d[0,-1,-1] + d[-1,-1,-1])/8.;
  fractions (phi, f);

  foreach()
    foreach_dimension()
      u.x[] = 0.;

  dump (file = "dumpInit");
  fprintf (stderr, "wrote dumpInit cells=%ld\n", grid->tn);
  return 1;
}
