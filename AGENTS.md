# hpc-basilisk-scaling

Stock Basilisk MPI kernel benchmarks on MareNostrum5 GPP. The first
EuroHPC Regular Access evidence is that unmodified `mpi-circle.c` and
`mpi-laplacian.c` from basilisk.fr compile, run, and scale on MN5.
Poisson is the bottleneck later physics sits on.

## Structure

```
.
├── simulationCases/ - unmodified Basilisk tests from basilisk.fr/src/test
├── scripts/ - local qcc source generation and MN5 staging/compile helpers
├── slurm/ - MareNostrum5 GPP smoke and scaling batch scripts
├── postProcess/ - timer-table parser and publication-style scaling plots
├── figures/ - generated PDFs (gitignored)
└── results/ - collected MN5 timer tables (gitignored raw trees)
```

## Stock sources

- `simulationCases/mpi-circle.c` is the 2D adaptive-mesh kernel test.
- `simulationCases/mpi-laplacian.c` is the Laplacian / restriction / Poisson
  kernel test. Generate the 3D octree C99 with `qcc -grid=octree`.
- `simulationCases/check_restriction.h` is required by `mpi-circle.c`.
- `simulationCases/marangoni.c` is the unmodified basilisk.fr
  `src/test/marangoni.c` (Al Saud et al. 2018). Do not edit it.
- `simulationCases/marangoni-scale.c` is the same physics with cluster I/O:
  no bview, a single LEVEL from argv, a short \(t/t_0\) window, rank-0
  logging. Default LEVEL 10 is 64 points per radius. Optional argv
  `DUMP_EVERY` (in \(t/t_0\); negative means no dumps) and `RESTART`.
  Periodic dumps write `snapshot-TSTAR`; a terminal dump writes `restart`.
  `#TIMING` includes RSS in kB when the run ends.
- Do not edit the unmodified stock copies. If a change is required, record
  why and keep a stock copy identifiable.

Pinned local Basilisk used to generate portable C99:

- darcs last patch `586963ed3f4e8704f89b314b8d1f9e8a475a4065`
  (Stephane Popinet, 2026-07-03, "Layers work with CUDA/HIP/OpenCL")
- repo weak hash `d988c85fac0fff4e4db82ca6c839972912bac005`

## Build and run

Local (machine with `qcc`):

```
export BASILISK="${BASILISK:-$(dirname "$(command -v qcc)")}"
bash scripts/generate-sources.sh
```

On MareNostrum5, never compute on a login node. Stage, compile and submit
through `mn5-login`:

```
bash scripts/stage-mn5.sh
ssh mn5-login 'bash /gpfs/projects/your_account/mn5-basilisk-scaling/scripts/compile-mn5.sh'
ssh mn5-login 'bash /gpfs/projects/your_account/mn5-basilisk-scaling/slurm/smoke.sh'
```

Account `your_account`. Use `gp_debug` only for a one-job compile/smoke.
Scale-up defaults to `gp_ehpc` (3-day wall, many jobs allowed). Builds
and output live under `/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling`.
Compact scripts stay under `/gpfs/projects/your_account/mn5-basilisk-scaling`.

On Snellius, never compute on a login node. Stage, compile and submit
through `snellius`:

```
bash scripts/stage-snellius.sh
ssh snellius 'bash -lc "bash /projects/0/your_project/hpc-basilisk-scaling/scripts/compile-snellius.sh"'
ssh snellius 'bash /projects/0/your_project/hpc-basilisk-scaling/slurm/snellius/smoke.sh'
ssh snellius 'bash /projects/0/your_project/hpc-basilisk-scaling/slurm/snellius/scale-extent.sh'
```

Account `your_account`, partition `genoa` (192 cores, 336 GB). Builds and
output live under `/scratch-shared/your_user/hpc-basilisk-scaling`. Compact
scripts stay under `/projects/0/your_project/hpc-basilisk-scaling`.
Collect with `scripts/collect-snellius.sh` and plot with
`--results results/latest --snellius results/snellius/latest`.
Uniform Marangoni wall-time/iteration is `postProcess/plot_walltime.py`.

## Guidelines

- Never hardcode a machine-local `qcc` path; resolve with `$BASILISK` or
  `which qcc`.
- Do not commit `basilisk/`, `.comphy-basilisk`, `.docker_mode`, generated
  C99, binaries, or raw HPC output.
- Component READMEs are public-candidate. Live timings, job IDs and
  debugging stay in the EuroHPC tracker and project `scratch/` until Vatsal
  approves promotion.
- Use `publication-plots` for every figure. Overlay official Curie/Occigen
  tables from `reference/` only when the mesh matches. Current campaign
  plots are `figures/laplacian-L9.pdf`, `figures/circle-L14.pdf`,
  `figures/circle-L12.pdf`, `figures/marangoni-uniform-per-iter.pdf`,
  `figures/planar-ndrop-per-iter.pdf`,
  `figures/marangoni-uniform-ndrop-per-iter.pdf` and
  `figures/marangoni-validate-vt-fields.pdf`.
  Published Curie "circle" tables are full 2D grids (\(2^{2L}\) cells).
- `CLAUDE.md` is local and gitignored; it only points at this file.
