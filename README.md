# HPC Basilisk scaling and showcase cases

[![Basilisk](https://img.shields.io/badge/Basilisk-C-blue)](http://basilisk.fr)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

MPI-ready [Basilisk C](http://basilisk.fr) kernels and two-phase cases
used to benchmark adaptive/uniform quadtrees on HPC systems, and to
make short field movies of the physics those kernels sit under.

Developed at the
[Computational Multiphase Physics (CoMPhy) Lab](https://comphy-lab.org/),
Durham University.

## Overview

Basilisk's pressure projection is a multigrid Poisson solve. This
repository keeps the official kernel tests that isolate that bottleneck,
then the same stack with Marangoni and chemically fuelled active-drop
physics so a rank sweep and a visualisation share one tree.

| Case | What it shows |
|---|---|
| `mpi-circle.c` | 2D adaptive mesh (Curie comparison) |
| `mpi-laplacian.c` | 3D octree Laplacian / Poisson (Occigen comparison) |
| `marangoni-scale.c` | Axisymmetric Al Saud drop, cluster I/O |
| `marangoni-multidrop.c` | Planar $n$-drop Marangoni, uniform or adaptive |
| `marangoni-interact.c` | Eight drops in a radial $\sigma$ well |
| `activity-drop.c` | Chemically fuelled drop(s): single or seven-drop layouts |

`marangoni.c` is the unmodified basilisk.fr `src/test/marangoni.c`
(Al Saud, Popinet and Tchelepi, 2018). Do not edit it. The `*-scale`
and `activity-drop` files add dump/restore and rank-0 logging for
cluster runs. Compile `marangoni-scale.c` / `marangoni-multidrop.c`
with `-DUNIFORM=1` to hold a uniform quadtree at the requested LEVEL.

## Physics

### Marangoni drop (Al Saud)

An insoluble drop in a linear or radial surface-tension gradient. The
integral CLSVOF formulation is that of basilisk.fr
`src/test/marangoni.c`. A linear $\sigma(x)$ translates an array of
drops as a rigid body; a radial well
$\sigma=\Gamma_0+B(x^2+y^2)$ drives them inward so they interact.

### Active drop

A chemically fuelled drop with an activity tracer $c$ in the outer
fluid. Surface tension is

$$\sigma = \frac{1}{\mathrm{Ca}} + 4c.$$

Activity flux at the interface and diffusion of $c$ (Péclet number
$\mathrm{Pe}$) produce Marangoni propulsion. The drop phase is $f=1$.
See [src-local/activity.h](src-local/activity.h). The solver is derived
from
[comphy-lab/active-drops-with-memory](https://github.com/comphy-lab/active-drops-with-memory)
(`dropMove.c` at `45ce373`), activity boundary condition only.

| Parameter | Meaning |
|---|---|
| $\mathrm{Oh}$ | Ohnesorge number (sets $\rho$ at $\mu=1$) |
| $\mathrm{Ca}$ | Capillary number (base $\sigma$) |
| $\mathrm{Pe}$ | Péclet number of $c$ |
| $\mathrm{AcNum}$ | Activity at the interface |
| `max_level` | Finest wavelet level (points per $R$ $\approx 2^{\mathrm{max\_level}}R/L_0$) |

## Basilisk (required)

First-time install (or reinstall):

```bash
curl -sL https://raw.githubusercontent.com/comphy-lab/basilisk-C/v2026-08-30/reset_install_basilisk-ref-locked.sh | bash -s -- --ref=v2026-08-30 --hard
```

Subsequent runs (reuses existing `basilisk/` if the ref matches):

```bash
curl -sL https://raw.githubusercontent.com/comphy-lab/basilisk-C/v2026-08-30/reset_install_basilisk-ref-locked.sh | bash -s -- --ref=v2026-08-30
```

When a newer stable release is available, replace `v2026-08-30` in both
the script URL and `--ref` with the same
[release tag](https://github.com/comphy-lab/basilisk-C/releases).

## Repository structure

```
.
├── simulationCases/ - kernel tests and two-phase showcase solvers
│   ├── mpi-circle.c - 2D adaptive-mesh kernel
│   ├── mpi-laplacian.c - 3D octree Laplacian / Poisson kernel
│   ├── check_restriction.h - required by mpi-circle.c
│   ├── marangoni.c - unmodified basilisk.fr Al Saud test
│   ├── marangoni-scale.c - axisymmetric Al Saud, dump/restore, short t/t0
│   ├── marangoni-multidrop.c - planar n-drop Marangoni
│   ├── marangoni-interact.c - eight drops, radial sigma well
│   ├── activity-drop.c - chemically fuelled drop solver
│   ├── activity-single.cfg - one-drop activity layout
│   └── activity-seven.cfg - seven custom-centred drops
├── src-local/ - headers used by activity-drop.c
│   └── activity.h - activity tracer transport
├── scripts/ - qcc -source generation and site staging/compile helpers
│   └── compile-activity-drop.sh - safe local/MPI compile (qcc in a copy)
├── slurm/ - site batch wrappers (MareNostrum5 GPP, Snellius)
├── postProcess/ - timer plots and planar/axi snapshot extractors
├── figures/ - generated PDFs
├── reference/ - published Curie/Occigen tables and marangoni.ref
└── results/ - collected timer tables
```

## Running

Never run a solver, `mpirun`, or a heavy compile on a shared-HPC login
node. Login nodes are for editing, status, transfer and job submission.
Use an allocated compute node, or the batch wrappers in `slurm/`.

Generate portable C99 on a machine that has `qcc`:

```bash
export BASILISK="${BASILISK:-$(dirname "$(command -v qcc)")}"
bash scripts/generate-sources.sh
```

Local MPI compile from the generated C99, or with `qcc` directly:

```bash
# kernels (from generated/)
mpicc -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 generated/_mpi-circle.c -o mpi-circle -lm

# activity drop (qcc rewrites included headers; use the helper)
bash scripts/compile-activity-drop.sh
CC99='mpicc -std=c99' bash scripts/compile-activity-drop.sh "$PWD/activity-drop"
```

Run on an allocated node:

```bash
mpirun -np 8 ./mpi-circle
mpirun -np 8 ./activity-drop --params simulationCases/activity-single.cfg
mpirun -np 8 ./activity-drop --params simulationCases/activity-seven.cfg
mpirun -np 8 ./marangoni-interact 8 12 0.1
```

`activity-drop` also accepts `key=value` overrides after `--params`.
Snapshots are `snapshot-%012.6f` in `output_dir` (`.` in the packaged
configs). Restore with `resume=1` and `restart_file=snapshot-...`.

Site-specific staging, compile and Slurm scripts live in `scripts/` and
`slurm/`. They are written for MareNostrum5 GPP and Snellius genoa; copy
the pattern rather than running another site's paths verbatim.

## Post-processing

Timer tables (Basilisk `out-*-*` and `#TIMING` lines). Put collected
logs in `results/latest` first (`scripts/collect-results.sh` /
`scripts/collect-snellius.sh`):

```bash
python3 postProcess/plot_scaling.py --results results/latest --outdir figures
python3 postProcess/plot_walltime.py --results results/latest --outdir figures
python3 postProcess/plot_ndrop.py --results results/latest --outdir figures
```

Axisymmetric Al Saud validation (drop speed, error vs pts/$R$, drop-frame
field) uses `postProcess/get_fields.c`, `get_facets.c` and
`plot_validate_two_panel.py`.

Planar field movies (activity $c$ trails, or Marangoni $|u|$):

```bash
python3 postProcess/plot_field_frames.py \
  --case-dir /path/to/snapshots \
  --work-dir /path/to/work \
  --field c --xmin -28 --xmax 28 --ymin -28 --ymax 28 \
  --vmin 0 --vmax 4 --cpus 4 \
  --video activity-seven.mp4 --time-math t

python3 postProcess/plot_field_frames.py \
  --case-dir /path/to/snapshots \
  --work-dir /path/to/work \
  --field speed --xmin -8 --xmax 8 --ymin -8 --ymax 8 \
  --vmin 0 --vmax 0.1 --cpus 4 \
  --video marangoni-interact.mp4 --time-math 't/t_0'
```

`plot_field_frames.py` compiles `get_fields_planar.c` and
`get_facets_planar.c` once, renders frames in batches of `--cpus`
(alias `--CPUs`), sorts by parsed snapshot time, and stitches with
ffmpeg as sequential `img_%06d.png` (all I-frames). Optional
`--exclude-times 1.0,2.0` drops named snapshot times (restart dumps).
`--max-frames` and `--skip-video` are for short checks.

Current kernel figures: `figures/laplacian-L9.pdf`,
`figures/circle-L14.pdf`, `figures/circle-L12.pdf`. Uniform-quadtree
Marangoni wall time per iteration:
`figures/marangoni-uniform-per-iter.pdf`. Planar drop-count series:
`figures/planar-ndrop-per-iter.pdf`. Combined two-panel:
`figures/marangoni-uniform-ndrop-per-iter.pdf`. Adaptive Al Saud
validation: `figures/marangoni-validate-vt-fields.pdf`.

## Licence

The stock tests are part of Basilisk and remain under the Basilisk GPLv3
licence. Wrapper scripts, cluster I/O variants and `activity-drop` in
this repository are also GPLv3. The activity tracer header is derived
from `comphy-lab/active-drops-with-memory`.
