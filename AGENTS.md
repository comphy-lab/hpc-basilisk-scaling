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
- Do not edit these files. If a change is required, record why and keep a
  stock copy identifiable.

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

## Guidelines

- Never hardcode a machine-local `qcc` path; resolve with `$BASILISK` or
  `which qcc`.
- Do not commit `basilisk/`, `.comphy-basilisk`, `.docker_mode`, generated
  C99, binaries, or raw MN5 output.
- Component READMEs are public-candidate. Live timings, job IDs and
  debugging stay in the EuroHPC tracker and project `scratch/` until Vatsal
  approves promotion.
- Use `publication-plots` for every figure. Overlay official Curie/Occigen
  tables from `reference/`. Current campaign plots are
  `figures/mn5-laplacian-L9.pdf` and `figures/mn5-circle-L14.pdf`.
- `CLAUDE.md` is local and gitignored; it only points at this file.
