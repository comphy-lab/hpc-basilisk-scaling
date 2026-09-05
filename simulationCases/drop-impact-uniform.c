/**
# Uniform-grid Newtonian drop impact (cluster)

Compact kernel from
[comphy-lab/Drop-Impact](https://github.com/comphy-lab/Drop-Impact)
`simulationCases/dropImpact.c` at `8c26452`. Axisymmetric
Navier--Stokes + VOF + tension on a uniform quadtree. Geometric
sphere, so MPI can initialise.

Basilisk `axi.h` puts the symmetry axis on the *bottom* boundary;
*left* is the wall. The drop sits at $(1.05,0)$ with $u_x=-1$ toward
that wall, matching `default.params` (`drop_x=1.05`,
`impact_velocity=-1`) rather than the file comments that call left the
axis.

Usage:

~~~
mpirun -np N ./drop-impact-uniform LEVEL [NITER]
~~~

Default LEVEL 10 is $1024^2$ cells on $L_0=8$. Default NITER 10.
After setup, `reset_perf()` starts the timed region; the kernel does
not dump.
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#define FILTERED 1
#include "two-phase.h"
#include "navier-stokes/conserving.h"
#include "tension.h"

#include <sys/resource.h>

int LEVEL = 10;
int NITER = 10;

const double We = 10.0, Ohd = 1e-2, Ohs = 1e-5;
const double drop_x = 1.05, drop_y = 0., drop_radius = 1.;
const double impact_velocity = -1.;

u.t[left] = dirichlet(0.0);
u.n[left] = dirichlet(0.0);
f[left] = dirichlet(0.0);
u.n[right] = neumann(0.);
p[right] = dirichlet(0.0);
u.n[top] = neumann(0.);
p[top] = dirichlet(0.0);

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    NITER = atoi (argv[2]);
  if (LEVEL < 6 || LEVEL > 14) {
    fprintf (stderr, "drop-impact-uniform: LEVEL=%d out of range [6,14]\n",
	     LEVEL);
    exit (1);
  }
  if (NITER < 1) {
    fprintf (stderr, "drop-impact-uniform: NITER=%d must be positive\n", NITER);
    exit (1);
  }

  L0 = 8.;
  X0 = 0.;
  Y0 = 0.;
  init_grid (1 << LEVEL);
  N = 1 << LEVEL;

  rho1 = 1.0, rho2 = 1e-3;
  mu1 = Ohd / sqrt(We), mu2 = Ohs / sqrt(We);
  f.sigma = 1.0 / We;
  TOLERANCE = 1e-4;
  CFL = 0.5;

  if (pid() == 0)
    fprintf (stderr,
	     "drop-impact-uniform LEVEL=%d npe=%d NITER=%d L0=%g We=%g\n",
	     LEVEL, npe(), NITER, L0, We);

  run();
}

event init (t = 0)
{
  fraction (f, sq(drop_radius) - (sq(x - drop_x) + sq(y - drop_y)));
  foreach() {
    u.x[] = impact_velocity * f[];
    u.y[] = 0.;
  }
  reset_perf();
}

event stop (i = NITER)
{
  struct rusage ru;
  getrusage (RUSAGE_SELF, &ru);
  long mem0 = ru.ru_maxrss, memmax = mem0;
  MPI_Reduce (&mem0, &memmax, 1, MPI_LONG, MPI_MAX, 0, MPI_COMM_WORLD);
  if (pid() == 0)
    fprintf (fout,
	     "#TIMING npe=%d level=%d cells=%ld steps=%d t=%g real=%g "
	     "speed=%g grid=uniform mem0_kB=%ld memmax_kB=%ld\n",
	     npe(), LEVEL, grid->tn, i, t, perf.t, perf.speed, mem0, memmax);
}
