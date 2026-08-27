/**
# Planar interacting Marangoni drops in a radial $\sigma$ well

Same CLSVOF + integral surface tension as basilisk.fr
`src/test/marangoni.c` (Al Saud, Popinet and Tchelepi, 2018), but
planar, with several drops, and with a **non-uniform** imposed
surface-tension field
\[
\sigma = \Gamma_0 + B(x^2+y^2).
\]
A linear $\sigma(x)$ translates the whole array as a rigid body, so
the drops never meet. The radial well has $|\nabla\sigma|$ pointing
outward, so the drops migrate toward the origin and interact.

Default: eight drops on a ring of radius $5R$ in a $16R$ box, $64$
points per radius. Snapshots skip $i=0$ because qcc registers this
event before `adapt`.

Usage:

~~~
mpirun -np N ./marangoni-interact NDROPS [TMAX_T0] [DUMP_EVERY] [RESTART]
~~~
*/

#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"

#include <math.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>

#define MAXDROPS 32
#define PTS_PER_R 64

int NDROPS = 8, LEVEL = 10, from_restart = 0;
double TMAX_T0 = 12., DUMP_EVERY = 0.1, RING = 5.;
double XC[MAXDROPS], YC[MAXDROPS];
char restart_file[256] = "";

const double R = 1. [1], NablaT = 1., Mu = 1., Rho = 1. [0];
const double Re = 0.066, Ca = 0.66;
const double Gamma_T = Re*sq(Mu)/(Rho*sq(R)*NablaT);
const double Gamma_0 = (Gamma_T*R*NablaT)/Ca;
const double t0 = Mu/(Gamma_T*NablaT);
const double Cdrop = 1., Cbulk = 1.;
/* $|\nabla\sigma|$ at $r=5R$ is $\sim 6$ times the linear Al Saud gradient. */
const double INTERACT_B = 0.04;
double U_drop;

scalar sigmaf[];

static void impose_sigma (void)
{
  foreach()
    sigmaf[] = Gamma_0 + INTERACT_B*(sq(x) + sq(y));
}

static void place_drops (void)
{
  size (16.*R);
  origin (- L0/2., - L0/2.);
  N = (int) (L0*PTS_PER_R/R + 0.5);
  LEVEL = 0;
  while ((1 << LEVEL) < N)
    LEVEL++;
  N = 1 << LEVEL;

  if (NDROPS == 1) {
    XC[0] = RING*R;
    YC[0] = 0.;
    return;
  }
  for (int k = 0; k < NDROPS; k++) {
    double theta = 2.*M_PI*k/NDROPS;
    XC[k] = RING*R*cos (theta);
    YC[k] = RING*R*sin (theta);
  }
}

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
    NDROPS = atoi (argv[1]);
  if (argc > 2)
    TMAX_T0 = atof (argv[2]);
  if (argc > 3)
    DUMP_EVERY = atof (argv[3]);
  if (argc > 4) {
    strncpy (restart_file, argv[4], sizeof(restart_file) - 1);
    restart_file[sizeof(restart_file) - 1] = '\0';
  }
  if (NDROPS < 1 || NDROPS > MAXDROPS) {
    fprintf (stderr, "marangoni-interact: NDROPS=%d out of range [1,%d]\n",
	     NDROPS, MAXDROPS);
    exit (1);
  }
  if (TMAX_T0 <= 0.) {
    fprintf (stderr, "marangoni-interact: TMAX_T0=%g must be positive\n",
	     TMAX_T0);
    exit (1);
  }

  place_drops();
  rho1 = rho2 = Rho;
  mu1 = mu2 = Mu;
  d.sigmaf = sigmaf;
  TOLERANCE = 1e-4 [*];

  U_drop = - 2./((2. + 3.*mu2/mu1)*(2. + Cdrop/Cbulk))*Gamma_T*R*NablaT/mu1;

  if (pid() == 0)
    fprintf (stderr,
	     "marangoni-interact ndrops=%d L0=%g LEVEL=%d pts/R=%g ring=%g "
	     "B=%g npe=%d TMAX/t0=%g dump/t0=%g restart=%s\n",
	     NDROPS, L0, LEVEL, N*R/L0, RING, INTERACT_B, npe(),
	     TMAX_T0, DUMP_EVERY,
	     restart_file[0] ? restart_file : "none");

  run();
}

event init (t = 0)
{
  if (restart_file[0]) {
    if (!restore (file = restart_file)) {
      fprintf (stderr, "marangoni-interact: cannot restore '%s'\n",
	       restart_file);
      exit (1);
    }
    from_restart = 1;
    N = 1 << LEVEL;
    if (pid() == 0)
      fprintf (stderr, "restored %s t/t0=%g cells=%ld npe=%d N=%d\n",
	       restart_file, t/t0, grid->tn, npe(), N);
  }
  else {
    foreach() {
      double dd = HUGE;
      for (int k = 0; k < NDROPS; k++)
	dd = min (dd, sqrt (sq(x - XC[k]) + sq(y - YC[k])) - R);
      d[] = dd;
    }
  }
  impose_sigma();
}

event properties (i++)
{
  impose_sigma();
}

double u_drop = 0.;

event logfile (i += 10)
{
  double xb = 0., yb = 0., vb = 0., sb = 0.;
  static double xb0 = 0., previous = 0.;
  if (t == 0.)
    previous = 0.;
  foreach (reduction(+:xb) reduction(+:yb) reduction(+:vb) reduction(+:sb)) {
    double dv = (1. - f[])*dv();
    vb += u.x[]*dv;
    xb += x*dv;
    yb += y*dv;
    sb += dv;
  }
  static double sb0 = 0.;
  if (pid() == 0) {
    if (i == 0) {
      sb0 = sb;
      fprintf (fout,
	       "t dsb xb yb rcm vb/U_drop ta u_drop/U_drop dt perf.t "
	       "perf.speed cells npe ndrops\n");
    }
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
    double rcm = sb > 0. ? sqrt (sq(xb/sb) + sq(yb/sb)) : 0.;
    fprintf (fout, "%g %g %g %g %g %g %g %g %g %g %g %ld %d %d\n",
	     t/t0, sb0 > 0. ? (sb - sb0)/sb0 : 0.,
	     sb > 0. ? xb/sb : 0., sb > 0. ? yb/sb : 0., rcm,
	     sb > 0. ? vb/sb/U_drop : 0.,
	     (t + previous)/2./t0, u_drop/U_drop,
	     dt, perf.t, perf.speed, grid->tn, npe(), NDROPS);
    fflush (fout);
  }
  else
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
  xb0 = sb > 0. ? xb/sb : 0.;
  previous = t;
}

#if TREE
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
      write the full $N^2$ tree. Wait one step. */
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
	     "#TIMING npe=%d ndrops=%d level=%d cells=%ld steps=%d t=%g "
	     "real=%g speed=%g u=%g grid=adaptive mem0_kB=%ld memmax_kB=%ld\n",
	     npe(), NDROPS, LEVEL, grid->tn, i, t/t0, perf.t, perf.speed,
	     u_drop/U_drop, mem0, memmax);
}
