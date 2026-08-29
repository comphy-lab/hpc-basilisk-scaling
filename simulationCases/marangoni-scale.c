/**
# Cluster Marangoni migration (stock physics)

This is the basilisk.fr `src/test/marangoni.c` case of Al Saud, Popinet
and Tchelepi, *J. Comput. Phys.* **371**, 896 (2018), section 3.4:
axisymmetric CLSVOF drop in a linear surface-tension (temperature)
gradient. The governing equations, fluid properties and integral
Marangoni coupling are unchanged.

The official test loops over levels 7--9 (8, 16 and 32 points per
radius) and writes a bview snapshot. That is the wrong I/O and the
wrong grid for an HPC strong-scaling sweep: the published velocity
ratio is still moving between those three resolutions, so the cluster
runs hold a *single* finer mesh and drop graphics.

Usage:

~~~
mpirun -np N ./marangoni-scale LEVEL [TMAX_T0] [DUMP_EVERY] [RESTART]
~~~

*LEVEL* is the maximum quadtree level. The domain is \(16R\), so the
number of points per radius is \(2^{\mathrm{LEVEL}-4}\). Default
LEVEL 10 is 64 points per radius, twice the finest official test.
LEVEL 12 is 256 points per radius.

*TMAX_T0* is the run length in units of \(t_0=\mu/(\Gamma_T\nabla T)\).
The official verification window is 3. Default 0.5 is long enough to
adapt the mesh and sample the Marangoni start-up without spending the
full terminal-velocity integration on every rank count.

*DUMP_EVERY* is the snapshot cadence in units of \(t_0\). Negative
(the default) writes no dump files, matching the rank-sweep campaign.
Zero dumps only the terminal `restart` file. Positive dumps
`snapshot-TSTAR` every *DUMP_EVERY* plus `restart` at the end. Each
dump line is `#IO dump ...` with wall time and file size.

*RESTART* is an optional Basilisk dump to restore before `run()`. The
restore is timed as `#IO restore ...`.

Compile with `-DUNIFORM=1` to keep the initial quadtree uniform at
LEVEL (no `adapt_wavelet`). That is the same TREE/MPI backend with
\(N^2\) cells instead of the interface-only adaptive count.

Rank 0 writes the time series to stdout and a one-line `#TIMING`
summary at the end, including per-rank and max RSS in kB. `run()`
still prints Basilisk's `timer_print` line.
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"

#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>

int LEVEL = 10;
int from_restart = 0;
double TMAX_T0 = 0.5;
double DUMP_EVERY = -1.;
char restart_file[256] = "";

const double R = 1. [1], NablaT = 1., Mu = 1., Rho = 1. [0];
const double Re = 0.066, Ca = 0.66;
const double Gamma_T = Re*sq(Mu)/(Rho*sq(R)*NablaT);
const double Gamma_0 = (Gamma_T*R*NablaT)/Ca;
const double t0 = Mu/(Gamma_T*NablaT);
const double Cdrop = 1., Cbulk = 1.;
double U_drop;

scalar sigmaf[];

static void timed_dump (const char * file)
{
  MPI_Barrier (MPI_COMM_WORLD);
  double t1 = MPI_Wtime();
  dump (file = file);
  MPI_Barrier (MPI_COMM_WORLD);
  double wall = MPI_Wtime() - t1;
  if (pid() == 0) {
    struct stat st;
    long bytes = stat (file, &st) == 0 ? (long) st.st_size : -1;
    fprintf (fout,
	     "#IO dump file=%s wall=%g bytes=%ld cells=%ld npe=%d t=%g\n",
	     file, wall, bytes, grid->tn, npe(), t/t0);
    fflush (fout);
  }
}

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    TMAX_T0 = atof (argv[2]);
  if (argc > 3)
    DUMP_EVERY = atof (argv[3]);
  if (argc > 4) {
    strncpy (restart_file, argv[4], sizeof(restart_file) - 1);
    restart_file[sizeof(restart_file) - 1] = '\0';
  }
  if (LEVEL < 6 || LEVEL > 16) {
    fprintf (stderr, "marangoni-scale: LEVEL=%d out of range [6,16]\n", LEVEL);
    exit (1);
  }
  if (TMAX_T0 <= 0.) {
    fprintf (stderr, "marangoni-scale: TMAX_T0=%g must be positive\n", TMAX_T0);
    exit (1);
  }

  size (16*R);
  origin (- L0/2.);
  rho1 = rho2 = Rho;
  mu1 = mu2 = Mu;
  d.sigmaf = sigmaf;
  TOLERANCE = 1e-4 [*];
  N = 1 << LEVEL;

  U_drop = - 2./((2. + 3.*mu2/mu1)*(2. + Cdrop/Cbulk))*Gamma_T*R*NablaT/mu1;

  if (pid() == 0)
    fprintf (stderr,
	     "marangoni-scale LEVEL=%d pts/R=%d npe=%d TMAX/t0=%g dump/t0=%g "
	     "restart=%s N=%d grid=%s\n",
	     LEVEL, N/16, npe(), TMAX_T0, DUMP_EVERY,
	     restart_file[0] ? restart_file : "none", N,
#ifdef UNIFORM
	     "uniform"
#else
	     "adaptive"
#endif
	     );

  run();
}

event init (t = 0)
{
  if (restart_file[0]) {
    MPI_Barrier (MPI_COMM_WORLD);
    double t1 = MPI_Wtime();
    if (!restore (file = restart_file)) {
      fprintf (stderr, "marangoni-scale: cannot restore '%s'\n", restart_file);
      exit (1);
    }
    MPI_Barrier (MPI_COMM_WORLD);
    double wall = MPI_Wtime() - t1;
    from_restart = 1;
    N = 1 << LEVEL;
    if (pid() == 0) {
      fprintf (stderr,
	       "restored %s t/t0=%g wall=%g cells=%ld npe=%d N=%d\n",
	       restart_file, t/t0, wall, grid->tn, npe(), N);
      fprintf (fout,
	       "#IO restore file=%s wall=%g cells=%ld npe=%d t=%g N=%d\n",
	       restart_file, wall, grid->tn, npe(), t/t0, N);
      fflush (fout);
    }
  }
  else
    foreach() {
      d[] = sqrt (sq(x) + sq(y)) - R;
      sigmaf[] = Gamma_0 + Gamma_T*NablaT*x;
    }
}

double u_drop = 0.;

event logfile (i += 10)
{
  double xb = 0., vb = 0., sb = 0.;
  static double xb0 = 0., previous = 0.;
  if (t == 0.)
    previous = 0.;
  foreach (reduction(+:xb) reduction(+:vb) reduction(+:sb)) {
    double dv = (1. - f[])*dv();
    vb += u.x[]*dv;
    xb += x*dv;
    sb += dv;
  }
  static double sb0 = 0.;
  static int header = 0;
  if (pid() == 0) {
    if (!header) {
      sb0 = sb;
      fprintf (fout,
	       "t dsb xb vb/U_drop ta u_drop/U_drop dt perf.t perf.speed cells npe\n");
      header = 1;
    }
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
    fprintf (fout, "%g %g %g %g %g %g %g %g %g %ld %d\n",
	     t/t0, sb0 > 0. ? (sb - sb0)/sb0 : 0., xb/sb, vb/sb/U_drop,
	     (t + previous)/2./t0, u_drop/U_drop,
	     dt, perf.t, perf.speed, grid->tn, npe());
    fflush (fout);
  }
  else
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
  xb0 = xb/sb, previous = t;
}

#if TREE && !defined(UNIFORM)
event adapt (i++) {
  adapt_wavelet ({f,u}, {1e-2, 1e-5, 1e-5}, LEVEL);
}
#endif

event snapshot (i++)
{
  static double next_dump = 0.;
  static int armed = 0;
  if (DUMP_EVERY > 0.) {
    if (!armed) {
      next_dump = from_restart ? t + DUMP_EVERY*t0 : 0.;
      armed = 1;
    }
    if (i == 0) {
      /**
      qcc registers this event before `adapt`, so a dump at i=0 would
      write the full \(N^2\) tree. Wait one step. */
    }
    else if (t + 1e-12 >= next_dump) {
      char name[80];
      snprintf (name, sizeof(name), "snapshot-%06.3f", t/t0);
      timed_dump (name);
      next_dump += DUMP_EVERY*t0;
    }
  }
}

event stop (t = TMAX_T0*t0)
{
  if (DUMP_EVERY >= 0.)
    timed_dump ("restart");

  struct rusage ru;
  getrusage (RUSAGE_SELF, &ru);
  long mem0 = ru.ru_maxrss, memmax = mem0;
  MPI_Reduce (&mem0, &memmax, 1, MPI_LONG, MPI_MAX, 0, MPI_COMM_WORLD);

  if (pid() == 0)
    fprintf (fout,
	     "#TIMING npe=%d level=%d cells=%ld steps=%d t=%g real=%g speed=%g u=%g grid=%s mem0_kB=%ld memmax_kB=%ld\n",
	     npe(), LEVEL, grid->tn, i, t/t0, perf.t, perf.speed,
	     u_drop/U_drop,
#ifdef UNIFORM
	     "uniform"
#else
	     "adaptive"
#endif
	     , mem0, memmax);
}
