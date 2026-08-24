# HPC Basilisk kernel scaling

Stock [Basilisk C](http://basilisk.fr) MPI tests on MareNostrum5 GPP
(Barcelona Supercomputing Center) and Snellius (SURF). The repository
records the steps used to show that the official adaptive-circle and
Laplacian/Poisson kernels compile and scale on the EuroHPC Benchmark
Access award `EHPC-BEN-2026B08-034`, and the same kernels on Snellius.

Developed at the
[Computational Multiphase Physics (CoMPhy) Lab](https://comphy-lab.org/),
Durham University.

## Why these two tests

Basilisk's pressure projection is a multigrid Poisson solve. The official
tests already isolate that kernel and the operators it is built from
(mesh traversal, Laplacian, restriction, load balance):

- [`mpi-circle.c`](http://basilisk.fr/src/test/mpi-circle.c) — 2D adaptive
  mesh, published on Curie
- [`mpi-laplacian.c`](http://basilisk.fr/src/test/mpi-laplacian.c) — 3D
  octree kernels, published on Occigen

The files in `simulationCases/` are unmodified copies of those tests, plus
the stock `marangoni.c` Marangoni-migration case (Al Saud et al., 2018)
and cluster I/O variants `marangoni-scale.c` / `marangoni-multidrop.c`
that keep the same equations. Those two cases can be compiled with
`-DUNIFORM=1` to hold a uniform quadtree at the requested LEVEL instead
of wavelet adaptation.

## Structure

```
.
├── simulationCases/ - unmodified Basilisk tests from basilisk.fr/src/test
├── scripts/ - local qcc source generation and HPC staging/compile helpers
├── slurm/ - MareNostrum5 GPP and Snellius smoke/scaling batch scripts
├── postProcess/ - timer-table parser and scaling plots
├── figures/ - generated PDFs
└── results/ - collected timer tables
```

## Requirements

- Local: Basilisk `qcc` (used only to emit portable C99)
- MareNostrum5 GPP: Intel MPI (`mpicc`), Slurm account `your_account`
- Snellius: OpenMPI 5 / GCC 13 (`foss` 2024 stack), Slurm account `your_account`, partition `genoa`

## Quick start

Generate portable C99 on a machine that has `qcc`:

```
bash scripts/generate-sources.sh
```

Stage the tree to MN5 project space, compile on a login node, and submit a
two-rank `gp_debug` smoke for both tests:

```
bash scripts/stage-mn5.sh
ssh mn5-login 'bash /gpfs/projects/your_account/mn5-basilisk-scaling/scripts/compile-mn5.sh'
ssh mn5-login 'bash /gpfs/projects/your_account/mn5-basilisk-scaling/slurm/smoke.sh'
```

Scale-up defaults to `gp_ehpc` (circle \(L=14\), laplacian \(L=9\), 1–32 nodes):

```
ssh mn5-login 'bash /gpfs/projects/your_account/mn5-basilisk-scaling/slurm/scale.sh'
```

The same official-extent rank list on Snellius genoa:

```bash
bash scripts/stage-snellius.sh
ssh snellius 'bash -lc "bash /projects/0/your_project/hpc-basilisk-scaling/scripts/compile-snellius.sh"'
ssh snellius 'bash /projects/0/your_project/hpc-basilisk-scaling/slurm/snellius/scale-extent.sh'
```

Plot collected `out-*-*` tables:

```bash
python3 postProcess/plot_scaling.py --results results/latest --snellius results/snellius/latest --outdir figures
```

Current kernel figures are `figures/laplacian-L9.pdf`,
`figures/circle-L14.pdf` and `figures/circle-L12.pdf`. The 3D octree
series is compared with Occigen. The 2D full-quadtree series is compared
with Curie: those published "circle" tables are \(N=2^{2L}\) cells, not
the adaptive `mpi-circle` mesh. Occigen has no \(L=8\) table, so
`laplacian-L8.pdf` is MareNostrum 5 and Snellius only.

Uniform-quadtree Marangoni (stock Al Saud drop, axisymmetric) wall time
per iteration versus MPI rank, 64--512 points per radius, is
`figures/marangoni-uniform-per-iter.pdf`.

## Licence

The stock tests are part of Basilisk and remain under the Basilisk GPLv3
licence. Wrapper scripts in this repository are also GPLv3.
