/**
# Planar multi-drop Marangoni migration (stock physics)

Same fluid properties, CLSVOF, integral surface tension and imposed
linear \(\sigma(x)\) as basilisk.fr `src/test/marangoni.c` (Al Saud et
al., 2018), but in planar two-dimensional geometry so that several
drops can sit in one box. The official test is axisymmetric and
cannot host a drop array.

Each drop is resolved with 64 cells across its radius. The square
domain grows with the drop count so that a \(4R\) centre-to-centre
pitch plus a one-radius margin still fits. That is the many-drop
physical scale-up: more interfaces, more adaptive cells, same drop
resolution.

Compile with `-DUNIFORM=1` to keep the initial quadtree uniform at
LEVEL (no `adapt_wavelet`). Same TREE/MPI backend, \(N^2\) cells.

Usage:

~~~
mpirun -np N ./marangoni-multidrop NDROPS [TMAX_T0]
~~~
*/

#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"

#define MAXDROPS 32
#define PTS_PER_R 64

int NDROPS = 2, LEVEL = 10, NX = 1, NY = 1;
double TMAX_T0 = 0.5, PITCH;
double XC[MAXDROPS], YC[MAXDROPS];

const double R = 1. [1], NablaT = 1., Mu = 1., Rho = 1. [0];
const double Re = 0.066, Ca = 0.66;
const double Gamma_T = Re*sq(Mu)/(Rho*sq(R)*NablaT);
const double Gamma_0 = (Gamma_T*R*NablaT)/Ca;
const double t0 = Mu/(Gamma_T*NablaT);
const double Cdrop = 1., Cbulk = 1.;
double U_drop;

scalar sigmaf[];

static void place_drops (void)
{
  NX = 1;
  NY = 1;
  while (NX*NY < NDROPS) {
    if (NX <= NY)
      NX++;
    else
      NY++;
  }
  PITCH = 4.*R;
  double need = max(NX, NY)*PITCH + 2.*R;
  double Lbox = 16.*R;
  while (Lbox + 1e-12 < need)
    Lbox *= 2.;
  size (Lbox);
  origin (- L0/2., - L0/2.);
  N = (int) (L0*PTS_PER_R/R + 0.5);
  LEVEL = 0;
  while ((1 << LEVEL) < N)
    LEVEL++;
  N = 1 << LEVEL;

  double x0 = -0.5*(NX - 1)*PITCH;
  double y0 = -0.5*(NY - 1)*PITCH;
  int k = 0;
  for (int j = 0; j < NY && k < NDROPS; j++)
    for (int i = 0; i < NX && k < NDROPS; i++) {
      XC[k] = x0 + i*PITCH;
      YC[k] = y0 + j*PITCH;
      k++;
    }
}

int main (int argc, char * argv[])
{
  if (argc > 1)
    NDROPS = atoi (argv[1]);
  if (argc > 2)
    TMAX_T0 = atof (argv[2]);
  if (NDROPS < 1 || NDROPS > MAXDROPS) {
    fprintf (stderr, "marangoni-multidrop: NDROPS=%d out of range [1,%d]\n",
	     NDROPS, MAXDROPS);
    exit (1);
  }
  if (TMAX_T0 <= 0.) {
    fprintf (stderr, "marangoni-multidrop: TMAX_T0=%g must be positive\n",
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
	     "marangoni-multidrop ndrops=%d grid=%dx%d L0=%g LEVEL=%d "
	     "pts/R=%g npe=%d TMAX/t0=%g grid=%s\n",
	     NDROPS, NX, NY, L0, LEVEL, N*R/L0, npe(), TMAX_T0,
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
  foreach() {
    double dd = HUGE;
    for (int k = 0; k < NDROPS; k++)
      dd = min (dd, sqrt (sq(x - XC[k]) + sq(y - YC[k])) - R);
    d[] = dd;
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
  if (pid() == 0) {
    if (i == 0) {
      sb0 = sb;
      fprintf (fout,
	       "t dsb xb vb/U_drop ta u_drop/U_drop dt perf.t perf.speed cells npe ndrops\n");
    }
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
    fprintf (fout, "%g %g %g %g %g %g %g %g %g %ld %d %d\n",
	     t/t0, sb0 > 0. ? (sb - sb0)/sb0 : 0., xb/sb, vb/sb/U_drop,
	     (t + previous)/2./t0, u_drop/U_drop,
	     dt, perf.t, perf.speed, grid->tn, npe(), NDROPS);
    fflush (fout);
  }
  else
    u_drop = t > previous ? (xb/sb - xb0)/(t - previous) : 0.;
  xb0 = xb/sb, previous = t;
}

event stop (t = TMAX_T0*t0)
{
  if (pid() == 0)
    fprintf (fout,
	     "#TIMING npe=%d ndrops=%d level=%d cells=%ld steps=%d t=%g real=%g speed=%g u=%g grid=%s\n",
	     npe(), NDROPS, LEVEL, grid->tn, i, t/t0, perf.t, perf.speed,
	     u_drop/U_drop,
#ifdef UNIFORM
	     "uniform"
#else
	     "adaptive"
#endif
	     );
}

#if TREE && !defined(UNIFORM)
event adapt (i++) {
  adapt_wavelet ({f,u}, {1e-2, 1e-5, 1e-5}, LEVEL);
}
#endif
