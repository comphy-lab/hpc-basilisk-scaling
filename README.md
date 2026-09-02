# HPC Basilisk scaling and showcase cases

[![Basilisk](https://img.shields.io/badge/Basilisk-C-blue)](http://basilisk.fr)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)

[Basilisk C](http://basilisk.fr) kernels and two-phase cases for measuring
how adaptive and uniform tree grids scale across MPI ranks, and for making
short field movies of the physics that sits on those grids. The stock kernel
tests are kept unmodified, so a run on a new machine lands on the same axes
as the timings published on basilisk.fr.

Developed at the
[Computational Multiphase Physics (CoMPhy) Lab](https://comphy-lab.org/),
Durham University.

## Why these cases

Every time step of an incompressible Basilisk run ends in a multigrid
Poisson solve for the pressure. On a tree grid that solve carries the
restriction and prolongation traffic between levels, and it is this traffic,
rather than the advection or the surface-tension terms, that sets the
strong-scaling limit. The stock tests `mpi-circle.c` and `mpi-laplacian.c`
time exactly these kernels, and basilisk.fr publishes their results on Curie
and Occigen. We keep both files unmodified and ship the published tables
under `reference/`, so a new machine can be compared against them directly.

The remaining cases put physics on the same stack. A gradient of surface
tension along an interface pulls the interface from low $\sigma$ towards
high $\sigma$, and the reaction drives the drop towards lower $\sigma$. Al
Saud, Popinet and Tchelepi (2018) verified the terminal velocity of an
axisymmetric drop in a linear gradient against theory, and their test seeds
the Marangoni cases here. Chemically fuelled drops set up the gradient
themselves: activity at the interface feeds a tracer into the outer fluid,
the tracer raises the surface tension where it accumulates, and the drop
moves away from its own wake. Each case gives a rank sweep and a field movie
from one source tree.

| Case | What it shows |
|---|---|
| `mpi-circle.c` | 2D adaptive mesh: refinement, restriction, Poisson (Curie comparison) |
| `mpi-laplacian.c` | 2D or 3D uniform Laplacian and Poisson (Occigen comparison) |
| `marangoni-scale.c` | Axisymmetric drop in a linear $\sigma$ gradient, cluster I/O |
| `marangoni-multidrop.c` | Planar lattice of $n$ drops, adaptive or uniform |
| `marangoni-interact.c` | Eight drops pulled into a radial $\sigma$ well |
| `activity-drop.c` | One or seven chemically fuelled drops |

`marangoni.c` is the unmodified basilisk.fr `src/test/marangoni.c`. The
`-scale`, `-multidrop`, `-interact` and `activity-drop` files keep its
physics and add what a cluster run needs: dump and restore, rank-0 logging,
and a terminal `#TIMING` line. Compile `marangoni-scale.c` or
`marangoni-multidrop.c` with `-DUNIFORM=1` to hold a uniform quadtree at the
requested LEVEL instead of adapting on the interface. Both variants use the
same TREE/MPI backend, so the comparison isolates the cost of adaptivity.

## Physics

### Marangoni migration

A drop of radius $R$ sits in a liquid whose surface tension varies linearly
along $x$. The tangential stress at the interface drives a flow towards
high $\sigma$, and the drop migrates in the opposite direction at a terminal
velocity $U_{\mathrm{drop}}$ that the theory of Al Saud et al. predicts.
Time is measured in $t_0 = \mu / (\Gamma_T \nabla T)$, with $\Gamma_T$ the
surface-tension coefficient and $\nabla T$ the imposed gradient. The
integral CLSVOF formulation is that of basilisk.fr `src/test/marangoni.c`.
The official test loops over 8, 16 and 32 points per radius and writes a
bview snapshot; the velocity ratio is still moving across those three
meshes, so the cluster variant holds one finer mesh (64 points per radius at
LEVEL 10) and drops the graphics.

The planar variant resolves each drop with 64 cells across its radius and
grows the box with the drop count, so a $4R$ pitch and a one-radius margin
always fit. A linear $\sigma(x)$ translates the whole array as a rigid body
and the drops never meet. The radial well $\sigma = \Gamma_0 + B(x^2+y^2)$
points $\nabla\sigma$ outward, so eight drops on a ring of radius $5R$ in a
$16R$ box migrate towards the origin and interact.

### Active drop

A chemically fuelled drop carries an activity tracer $c$ in the outer fluid.
Surface tension is

$$\sigma = \frac{1}{\mathrm{Ca}} + 4c.$$

Activity imposes a flux of $c$ at the interface, and $c$ diffuses with
Péclet number $\mathrm{Pe}$. Because $c$ raises $\sigma$, the Marangoni
stress points away from the trail the drop leaves behind, and the drop
propels itself. The drop phase is $f = 1$. The tracer transport lives in
[src-local/activity.h](src-local/activity.h); the solver is the
activity-boundary-condition branch of
[comphy-lab/active-drops-with-memory](https://github.com/comphy-lab/active-drops-with-memory)
(`dropMove.c` at `45ce373`).

| Parameter | Meaning |
|---|---|
| $\mathrm{Oh}$ | Ohnesorge number (sets $\rho$ at $\mu = 1$) |
| $\mathrm{Ca}$ | Capillary number (base surface tension) |
| $\mathrm{Pe}$ | Péclet number of $c$ |
| $\mathrm{AcNum}$ | Activity at the interface |
| `max_level` | Finest wavelet level (points per $R$ $\approx 2^{\mathrm{max\_level}} R / L_0$) |

The packaged layouts share $\mathrm{Oh} = 1$, $\mathrm{Ca} = 0.1$,
$\mathrm{Pe} = 1.6$ and $\mathrm{AcNum} = 1$ at `max_level` 10.
`activity-single.cfg` places one drop in a $10R$ box (about 102 points per
radius); `activity-seven.cfg` places seven drops at custom centres in a
$56R$ box.

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

```text
.
├── simulationCases/ - kernel tests and two-phase showcase solvers
│   ├── mpi-circle.c - 2D adaptive-mesh kernel
│   ├── mpi-laplacian.c - 2D/3D Laplacian and Poisson kernel
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
├── scripts/ - qcc -source generation, site staging and compile helpers
│   ├── site-env.sh - loads site/<name>.env and checks it
│   └── compile-activity-drop.sh - safe local/MPI compile (qcc in a copy)
├── site/ - per-cluster account and path templates (*.env.example)
├── slurm/ - batch wrappers for MareNostrum5 GPP (slurm/) and Snellius (slurm/snellius/)
├── postProcess/ - timer plots and planar/axi snapshot extractors
├── figures/ - generated PDFs and timing tables
├── reference/ - published Curie/Occigen tables and marangoni.ref
└── results/ - collected timer tables
```

## Running

Never run a solver, `mpirun` or a heavy compile on a shared-HPC login node.
Login nodes are for editing, status, transfer and job submission. Use an
allocated compute node or the batch wrappers in `slurm/`.

### On your own machine

Generate portable C99 on a machine that has `qcc`:

```bash
export BASILISK="${BASILISK:-$(dirname "$(command -v qcc)")}"
bash scripts/generate-sources.sh
```

Compile the kernels from the generated C99 with any MPI compiler, and the
active-drop solver through its helper (`qcc` rewrites included headers next
to the translation unit, so the helper works on a copy):

```bash
mpicc -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 generated/_mpi-circle.c -o mpi-circle -lm
mpicc -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 generated/_marangoni-scale.c -o marangoni-scale -lm
mpicc -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 generated/_marangoni-interact.c -o marangoni-interact -lm

bash scripts/compile-activity-drop.sh
CC99='mpicc -std=c99' bash scripts/compile-activity-drop.sh "$PWD/activity-drop"
```

Run on an allocated node:

```bash
mpirun -np 8 ./mpi-circle
mpirun -np 8 ./marangoni-scale 10 0.5
mpirun -np 8 ./marangoni-interact 8 12 0.1
mpirun -np 8 ./activity-drop --params simulationCases/activity-single.cfg
mpirun -np 8 ./activity-drop --params simulationCases/activity-seven.cfg
```

`marangoni-scale` takes `LEVEL [TMAX_T0] [DUMP_EVERY] [RESTART]`; a
negative `DUMP_EVERY` (the default) writes no snapshots, zero writes only
the terminal `restart`, and a positive value writes `snapshot-TSTAR` at that
cadence in $t_0$. `activity-drop` accepts `key=value` overrides after
`--params`, writes `snapshot-%012.6f` in `output_dir` (`.` in the packaged
configs), and restores with `resume=1` and `restart_file=snapshot-...`.

### On a cluster

The wrappers read the account, project and scratch paths and SSH aliases
of each site from `site/<site>.env`, which is ignored by Git. Copy the
template and fill it in once per site:

```bash
cp site/mn5.env.example site/mn5.env             # MareNostrum5 GPP
cp site/snellius.env.example site/snellius.env   # Snellius
```

Stage from your machine, then compile and submit on the login node. The
compile step is a short serial build of a few pre-generated C99 files,
which is the kind of work a login node is for; every solver run goes
through `sbatch`. The staging script copies the compact tree, including
`site/`, to `PROJECT_DST` and the generated C99 to `SCRATCH_DST`:

```bash
bash scripts/stage-mn5.sh
ssh <login-alias> 'bash <PROJECT_DST>/scripts/compile-mn5.sh'
ssh <login-alias> 'bash <PROJECT_DST>/slurm/smoke.sh'
```

The Snellius sequence is the same with `stage-snellius.sh`,
`compile-snellius.sh` and the wrappers under `slurm/snellius/`. Each
wrapper submits one campaign: `smoke*.sh` for a two-rank check,
`scale.sh` and `scale-extent.sh` for the kernel rank lists,
`scale-marangoni*.sh` for the drop cases, and `scale-marangoni-io-validate.sh`
for a timed dump-and-restart plus the Al Saud resolution study. Rank lists,
levels and windows are environment variables with sensible defaults; read
the header of the wrapper before changing them.

Two site facts shape the wrappers. A MareNostrum5 GPP node has 112 cores
and does not accept `--mem`, so a sub-node job takes one exclusive node and
`run.sbatch` launches the requested `RANKS` rather than `SLURM_NTASKS`. A
Snellius genoa node has 192 cores, and its memory follows the allocated
cores, so sub-node jobs pad `cpus-per-task` to keep the whole node. Copy
these patterns for another site rather than running one site's paths
verbatim.

## Post-processing

Timer tables come from the Basilisk `out-LEVEL-RANKS` files and the
`#TIMING` lines. Collect them into `results/latest` (and
`results/snellius/latest`) with `scripts/collect-results.sh` and
`scripts/collect-snellius.sh`, then plot:

```bash
python3 postProcess/plot_scaling.py --results results/latest --outdir figures
python3 postProcess/plot_walltime.py --results results/latest --outdir figures
python3 postProcess/plot_ndrop.py --results results/latest --outdir figures
```

Add `--snellius results/snellius/latest` to overlay the second machine.
`plot_scaling.py` overlays the published Curie and Occigen tables only when
the mesh matches; the Curie `mpi-circle` tables are full 2D grids with
$2^{2L}$ cells, not the adaptive mesh.

The axisymmetric Al Saud validation (drop speed against time, relative
error against points per radius, and the drop-frame velocity field) uses
`postProcess/get_fields.c`, `get_facets.c` and
`plot_validate_two_panel.py` with `reference/marangoni.ref`.

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
`get_facets_planar.c` once, renders frames in batches of `--cpus`, sorts
them by the parsed snapshot time and stitches them with ffmpeg as
sequential `img_%06d.png` (all I-frames). `--exclude-times 1.0,2.0` drops
named snapshot times such as restart dumps; `--max-frames` and
`--skip-video` are for short checks. Do not point this planar pipeline at
the axisymmetric `get_fields.c`.

Current figures: kernel scaling in `figures/laplacian-L9.pdf`,
`figures/circle-L14.pdf` and `figures/circle-L12.pdf`; uniform-quadtree
Marangoni wall time per iteration in `figures/marangoni-uniform-per-iter.pdf`;
the planar drop-count series in `figures/planar-ndrop-per-iter.pdf`; both
together in `figures/marangoni-uniform-ndrop-per-iter.pdf`; and the
adaptive Al Saud validation in `figures/marangoni-validate-vt-fields.pdf`.
The timing tables behind them are the CSV files beside the PDFs.

## Licence

The stock tests are part of Basilisk and remain under the Basilisk GPLv3
licence. Wrapper scripts, cluster I/O variants and `activity-drop` in this
repository are also GPLv3. The activity tracer header is derived from
`comphy-lab/active-drops-with-memory`.
