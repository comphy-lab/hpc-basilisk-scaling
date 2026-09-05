/**
# Uniform-grid bursting bubble (cluster)

Compact kernel from
[comphy-lab/Bursting-Bubble](https://github.com/comphy-lab/Bursting-Bubble)
`simulationCases/burstingBubble.c` at `aa69c79`. Axisymmetric
Navier--Stokes + VOF + tension on a uniform quadtree. The interface
comes from `DataFiles/Bo0.0010.dat` through Basilisk `distance.h`,
which is not MPI-safe, so the serial binary writes `dumpInit` and
stops. The MPI binary restores that dump, calls `reset_perf()`, and
advances `NITER` solver steps with no further dumps.

Usage:

~~~
./bursting-uniform-init LEVEL
mpirun -np N ./bursting-uniform LEVEL [NITER] [RESTART]
~~~

Default LEVEL 10 is $1024^2$ cells. Default NITER 10. Compile the
serial binary from `qcc -source` without `-D_MPI=1`; the MPI binary
with `-D_MPI=1`.
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#define FILTERED 1
#include "two-phase.h"
#include "navier-stokes/conserving.h"
#include "tension.h"

#if !_MPI
#include "distance.h"
#endif

#include <string.h>
#include <sys/resource.h>

int LEVEL = 10;
int NITER = 10;
char restart_file[256] = "dumpInit";

const double Oh = 1e-2, Oha = 1e-5, Bond = 1e-3, zWall = 0.05;

u.n[right] = neumann(0.);
p[right] = dirichlet(0.);
f[left] = dirichlet(1.0);
u.n[left] = dirichlet(0.0);
u.t[left] = dirichlet(0.0);

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    NITER = atoi (argv[2]);
  if (argc > 3) {
    strncpy (restart_file, argv[3], sizeof(restart_file) - 1);
    restart_file[sizeof(restart_file) - 1] = '\0';
  }
  if (LEVEL < 6 || LEVEL > 14) {
    fprintf (stderr, "bursting-uniform: LEVEL=%d out of range [6,14]\n", LEVEL);
    exit (1);
  }
  if (NITER < 1) {
    fprintf (stderr, "bursting-uniform: NITER=%d must be positive\n", NITER);
    exit (1);
  }

  L0 = fmin (zWall + 6., 16.);
  origin (-2. - zWall, 0.);
  init_grid (1 << LEVEL);
  N = 1 << LEVEL;

  rho1 = 1., rho2 = 1e-3;
  mu1 = Oh, mu2 = Oha;
  f.sigma = 1.0;
  CFL = 0.5;
  TOLERANCE = 1e-4;

  if (pid() == 0)
    fprintf (stderr,
	     "bursting-uniform LEVEL=%d npe=%d NITER=%d restart=%s L0=%g\n",
	     LEVEL, npe(), NITER, restart_file, L0);

  run();
}

event init (t = 0)
{
#if _MPI
  if (!restore (file = restart_file)) {
    fprintf (stderr, "bursting-uniform: cannot restore '%s'\n", restart_file);
    exit (1);
  }
  N = 1 << LEVEL;
  if (pid() == 0)
    fprintf (stderr, "restored %s t=%g cells=%ld npe=%d\n",
	     restart_file, t, grid->tn, npe());
  reset_perf();
#else
  char filename[80];
  snprintf (filename, sizeof(filename), "DataFiles/Bo%5.4f.dat", Bond);
  FILE * fp = fopen (filename, "rb");
  if (!fp) {
    snprintf (filename, sizeof(filename), "../DataFiles/Bo%5.4f.dat", Bond);
    fp = fopen (filename, "rb");
  }
  if (!fp) {
    fprintf (stderr, "bursting-uniform: missing DataFiles/Bo%5.4f.dat\n", Bond);
    exit (1);
  }
  coord * shape = input_xy (fp);
  fclose (fp);
  scalar d[];
  distance (d, shape);
  vertex scalar phi[];
  foreach_vertex()
    phi[] = -(d[] + d[-1] + d[0,-1] + d[-1,-1])/4.;
  fractions (phi, f);
  dump (file = "dumpInit");
  fprintf (stderr, "wrote dumpInit cells=%ld\n", grid->tn);
  return 1;
#endif
}

#if _MPI
/* i++ is INC-only and does not keep run(). i = NITER is INIT (a keeper). */
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
#endif
