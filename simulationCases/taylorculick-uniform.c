/**
# Uniform-grid elastic Taylor--Culick retraction (cluster)

Compact kernel from
[comphy-lab/Taylor-Culick-ViscoElastic](https://github.com/comphy-lab/Taylor-Culick-ViscoElastic)
`simulationCases/TaylorCulick.c` at `c0e3fa0`, with the scalar
log-conformation headers vendored in `src-local/`. Axisymmetric
two-phase VE on a uniform quadtree. The sheet is geometric
(`fraction()`), so MPI can initialise. No `adapt_wavelet`. After
setup, `reset_perf()` starts the timed region; the kernel does not dump.

Usage:

~~~
mpirun -np N ./taylorculick-uniform LEVEL [NITER]
~~~

Default LEVEL 10 is $1024^2$ cells on $L_0=100$. Default NITER 10.
Compile through `scripts/generate-sources.sh` so `qcc` sees a copy of
`src-local/`, not the tracked headers.
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#define FILTERED
#include "src-local/log-conform-viscoelastic-scalar-2D.h"
#include "src-local/two-phaseVE.h"
#include "navier-stokes/conserving.h"
#include "tension.h"

#include <sys/resource.h>

int LEVEL = 10;
int NITER = 10;

u.n[top] = neumann(0.);
p[top] = dirichlet(0.);
u.n[right] = neumann(0.);
p[right] = dirichlet(0.);

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    NITER = atoi (argv[2]);
  if (LEVEL < 6 || LEVEL > 14) {
    fprintf (stderr, "taylorculick-uniform: LEVEL=%d out of range [6,14]\n",
	     LEVEL);
    exit (1);
  }
  if (NITER < 1) {
    fprintf (stderr, "taylorculick-uniform: NITER=%d must be positive\n", NITER);
    exit (1);
  }

  L0 = 100.;
  X0 = 0.;
  Y0 = 0.;
  init_grid (1 << LEVEL);
  N = 1 << LEVEL;

  rho1 = 1., mu1 = 5e-2;
  rho2 = 1e-3, mu2 = 1e-5;
  G1 = 1., lambda1 = 1e30;
  G2 = 0., lambda2 = 0.;
  TOLelastic = 1e-2;
  f.sigma = 1.;
  TOLERANCE = 1e-4;
  CFL = 0.5;

  if (pid() == 0)
    fprintf (stderr,
	     "taylorculick-uniform LEVEL=%d npe=%d NITER=%d L0=%g\n",
	     LEVEL, npe(), NITER, L0);

  run();
}

event init (t = 0)
{
  const double hole0 = 1., h0 = 1.;
  fraction (f, y < hole0 + h0/2.
	    ? sq(h0/2.) - (sq(x) + sq(y - h0/2. - hole0))
	    : h0/2. - x);

  const double yrim = hole0 + h0/2.;
  const double expected = (h0/2.)*(sq(L0) - sq(yrim))/2.
    + (pi*sq(h0)/8.)*yrim;
  double vol = 0.;
  foreach (reduction(+:vol))
    vol += f[]*dv();
  if (pid() == 0)
    fprintf (stderr,
	     "initial liquid volume/(2 pi) = %g (expected %g, rel %.3g)\n",
	     vol, expected, fabs (vol - expected)/expected);
  if (fabs (vol - expected) > 0.05*expected) {
    fprintf (stderr, "taylorculick-uniform: initial sheet volume is wrong\n");
    exit (1);
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
