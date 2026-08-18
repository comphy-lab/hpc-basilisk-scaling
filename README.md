# MN5 Basilisk kernel scaling

Stock [Basilisk C](http://basilisk.fr) MPI tests on MareNostrum5 GPP
(Barcelona Supercomputing Center). The repository records the steps used
to show that the official adaptive-circle and Laplacian/Poisson kernels
compile and scale on the EuroHPC Benchmark Access award
`EHPC-BEN-2026B08-034`.

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

The files in `simulationCases/` are unmodified copies of those tests.

## Structure

```
.
├── simulationCases/ - unmodified Basilisk tests from basilisk.fr/src/test
├── scripts/ - local qcc source generation and MN5 staging/compile helpers
├── slurm/ - MareNostrum5 GPP smoke and scaling batch scripts
├── postProcess/ - timer-table parser and scaling plots
├── figures/ - generated PDFs
└── results/ - collected MN5 timer tables
```

## Requirements

- Local: Basilisk `qcc` (used only to emit portable C99)
- MareNostrum5 GPP: Intel MPI (`mpicc`), Slurm account `your_account`

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

Plot collected `out-*-*` tables:

```
python3 postProcess/plot_scaling.py --results results/latest --outdir figures
```

Current campaign figures are `figures/mn5-laplacian-L9.pdf` and
`figures/mn5-circle-L14.pdf`. The thinner `gp_debug` \(L=8\) / \(L=12\)
set is kept beside them.

## Licence

The stock tests are part of Basilisk and remain under the Basilisk GPLv3
licence. Wrapper scripts in this repository are also GPLv3.
