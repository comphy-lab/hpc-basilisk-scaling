/**
# Uniform-grid 3D viscoelastic drop impact (cluster)

Compact kernel from
[comphy-lab/Viscoelastic3D](https://github.com/comphy-lab/Viscoelastic3D)
`simulationCases/dropImpact.c` at `8c5ac69`, with the scalar 3D
log-conformation headers vendored in `src-local/`. Octree + geometric
sphere, so MPI can initialise. No `adapt_wavelet`. After setup,
`reset_perf()` starts the timed region; the kernel does not dump.

Usage:

~~~
mpirun -np N ./ve3d-impact-uniform LEVEL [NITER]
~~~

Default LEVEL 7 is $128^3$ cells on $L_0=4$. Default NITER 10.
Compile through `scripts/generate-sources.sh` (`qcc -grid=octree`).
*/

#include "grid/octree.h"
#include "navier-stokes/centered.h"

#define FILTERED
#include "src-local/log-conform-viscoelastic-scalar-3D.h"
#include "src-local/two-phaseVE.h"
#include "navier-stokes/conserving.h"
#include "tension.h"

#include <sys/resource.h>

int LEVEL = 7;
int NITER = 10;

#define xDist (5e-2)
#define R2(x, y, z) (sq(x - 1. - xDist) + sq(y) + sq(z))

f[left] = dirichlet(0.0);

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    NITER = atoi (argv[2]);
  if (LEVEL < 5 || LEVEL > 9) {
    fprintf (stderr, "ve3d-impact-uniform: LEVEL=%d out of range [5,9]\n",
	     LEVEL);
    exit (1);
  }
  if (NITER < 1) {
    fprintf (stderr, "ve3d-impact-uniform: NITER=%d must be positive\n", NITER);
    exit (1);
  }

  L0 = 4.0;
  init_grid (1 << LEVEL);
  N = 1 << LEVEL;

  const double We = 5.0, Oh = 1e-2, Oha = 1e-4, De = 1.0, Ec = 1.0;
  rho1 = 1.0, rho2 = 1e-3;
  mu1 = Oh / sqrt(We), mu2 = Oha / sqrt(We);
  G1 = Ec / We, G2 = 0.0;
  lambda1 = De * sqrt(We), lambda2 = 0.0;
  f.sigma = 1.0 / We;
  TOLERANCE = 1e-4;
  CFL = 0.5;

  if (pid() == 0)
    fprintf (stderr,
	     "ve3d-impact-uniform LEVEL=%d npe=%d NITER=%d L0=%g\n",
	     LEVEL, npe(), NITER, L0);

  run();
}

event init (t = 0)
{
  fraction (f, 1. - R2(x, y, z));
  foreach()
    u.x[] = -f[] * 1.0;
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
