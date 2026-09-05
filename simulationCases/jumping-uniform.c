/**
# Uniform-grid jumping-drops MPI continuation (cluster)

MPI second phase from
[comphy-lab/Jumping-Drops](https://github.com/comphy-lab/Jumping-Drops)
`jumpingDrops_main.c` at `f4ea474`. Restores the serial `dumpInit` and
advances `NITER` steps on a uniform octree. Does not include
`distance.h` or `jumpingDrops_common.h` (the latter always registers
`adapt_wavelet`). Gravity $G_y=-\mathrm{Bo}$ matches the serial init.
After restore, `reset_perf()` starts the timed region; the MPI binary
does not dump.

Usage:

~~~
mpirun -np N ./jumping-uniform LEVEL [NITER] [RESTART]
~~~

Default LEVEL 7 is $128^3$ cells, NITER 10, RESTART `dumpInit`.
*/

#include "grid/octree.h"
#include "navier-stokes/centered.h"
#define FILTERED 1
#include "two-phase.h"
#include "navier-stokes/conserving.h"
#include "tension.h"
#include "reduced.h"

#include <string.h>
#include <sys/resource.h>

int LEVEL = 7;
int NITER = 10;
double Oh = 0.005, Bo = 0.001;
char restart_file[256] = "dumpInit";

#define Rho21 (1.00e-3)
#define Mu21 (1.00e-2)

u.t[bottom] = dirichlet(0.);
u.r[bottom] = dirichlet(0.);
f[bottom] = dirichlet(0.);

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
  if (LEVEL < 5 || LEVEL > 8) {
    fprintf (stderr, "jumping-uniform: LEVEL=%d out of range [5,8]\n", LEVEL);
    exit (1);
  }
  if (NITER < 1) {
    fprintf (stderr, "jumping-uniform: NITER=%d must be positive\n", NITER);
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
  TOLERANCE = 1e-4;
  CFL = 0.5;

  if (pid() == 0)
    fprintf (stderr,
	     "jumping-uniform LEVEL=%d npe=%d NITER=%d restart=%s\n",
	     LEVEL, npe(), NITER, restart_file);

  run();
}

event init (t = 0)
{
  if (!restore (file = restart_file)) {
    fprintf (stderr, "jumping-uniform: cannot restore '%s'\n", restart_file);
    exit (1);
  }
  N = 1 << LEVEL;
  if (pid() == 0)
    fprintf (stderr, "restored %s t=%g cells=%ld npe=%d\n",
	     restart_file, t, grid->tn, npe());
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
