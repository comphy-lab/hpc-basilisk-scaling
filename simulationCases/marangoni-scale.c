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
mpirun -np N ./marangoni-scale LEVEL [TMAX_T0]
~~~

*LEVEL* is the maximum quadtree level. The domain is \(16R\), so the
number of points per radius is \(2^{\mathrm{LEVEL}-4}\). Default
LEVEL 10 is 64 points per radius, twice the finest official test.
LEVEL 12 is 256 points per radius.

*TMAX_T0* is the run length in units of \(t_0=\mu/(\Gamma_T\nabla T)\).
The official verification window is 3. Default 0.5 is long enough to
adapt the mesh and sample the Marangoni start-up without spending the
full terminal-velocity integration on every rank count.

Compile with `-DUNIFORM=1` to keep the initial quadtree uniform at
LEVEL (no `adapt_wavelet`). That is the same TREE/MPI backend with
\(N^2\) cells instead of the interface-only adaptive count.

Rank 0 writes the time series to stdout and a one-line `#TIMING`
summary at the end. `run()` still prints Basilisk's `timer_print`
line.
*/

#include "axi.h"
#include "navier-stokes/centered.h"
#include "two-phase-clsvof.h"
#include "integral.h"

int LEVEL = 10;
double TMAX_T0 = 0.5;

const double R = 1. [1], NablaT = 1., Mu = 1., Rho = 1. [0];
const double Re = 0.066, Ca = 0.66;
const double Gamma_T = Re*sq(Mu)/(Rho*sq(R)*NablaT);
const double Gamma_0 = (Gamma_T*R*NablaT)/Ca;
const double t0 = Mu/(Gamma_T*NablaT);
const double Cdrop = 1., Cbulk = 1.;
double U_drop;

scalar sigmaf[];

int main (int argc, char * argv[])
{
  if (argc > 1)
    LEVEL = atoi (argv[1]);
  if (argc > 2)
    TMAX_T0 = atof (argv[2]);
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
	     "marangoni-scale LEVEL=%d pts/R=%d npe=%d TMAX/t0=%g N=%d grid=%s\n",
	     LEVEL, N/16, npe(), TMAX_T0, N,
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
  if (pid() == 0) {
    if (i == 0) {
      sb0 = sb;
      fprintf (fout,
	       "t dsb xb vb/U_drop ta u_drop/U_drop dt perf.t perf.speed cells npe\n");
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

event stop (t = TMAX_T0*t0)
{
  if (pid() == 0)
    fprintf (fout,
	     "#TIMING npe=%d level=%d cells=%ld steps=%d t=%g real=%g speed=%g u=%g grid=%s\n",
	     npe(), LEVEL, grid->tn, i, t/t0, perf.t, perf.speed,
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
