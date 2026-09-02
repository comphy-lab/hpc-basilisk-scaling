# AGENTS.md

This is the operating manual for anyone, human or agent, who changes this
repository. `README.md` is the map for readers. This file says how to change
things without breaking the comparisons the repository exists to make: the
stock kernels against the published Curie and Occigen tables, and the
two-phase cases against the Al Saud terminal velocity.

## What stays fixed

- `simulationCases/mpi-circle.c`, `mpi-laplacian.c` and
  `check_restriction.h` are the unmodified basilisk.fr kernel tests. Their
  timings are only comparable with `reference/` while they stay unmodified.
- `simulationCases/marangoni.c` is the unmodified basilisk.fr
  `src/test/marangoni.c` (Al Saud, Popinet and Tchelepi, 2018). Do not edit
  it. If a change is ever required, record why and keep a stock copy
  identifiable.
- `reference/` holds published tables and the basilisk.fr terminal-velocity
  reference. It is reference data, never a place for our own runs.
- The portable C99 is generated from a pinned local Basilisk: darcs last
  patch `586963ed3f4e8704f89b314b8d1f9e8a475a4065` (Stephane Popinet,
  2026-07-03, "Layers work with CUDA/HIP/OpenCL"), repo weak hash
  `d988c85fac0fff4e4db82ca6c839972912bac005`. The README install tag is
  the supported way for a reader to obtain a compatible `qcc`; this pin
  records the tree that produced the C99 staged for the campaigns. Note
  a new pin here when the sources are regenerated from a different tree.

## Layout

```text
.
├── simulationCases/ - kernel tests and two-phase showcase solvers
├── src-local/ - activity.h for activity-drop.c
├── scripts/ - qcc -source generation, site-env loader, staging and compile helpers
├── site/ - *.env.example templates; real *.env files are ignored
├── slurm/ - MareNostrum5 GPP wrappers; slurm/snellius/ for Snellius
├── postProcess/ - timer plots; axi get_fields/get_facets; planar movie pipeline
├── figures/ - tracked PDFs and CSV timing tables
├── reference/ - published Curie/Occigen tables and marangoni.ref
└── results/ - collected timer trees (ignored except .gitkeep)
```

## Cases

- `marangoni-scale.c` is the Al Saud physics with cluster I/O: no bview, one
  LEVEL from argv, a short $t/t_0$ window, rank-0 logging. The domain is
  $16R$, so LEVEL 10 is 64 points per radius. Optional argv `DUMP_EVERY`
  (in $t_0$; negative means no dumps, zero means only the terminal
  `restart`) and `RESTART`. Periodic dumps are `snapshot-TSTAR`. The
  `#TIMING` line includes RSS in kB at the end of the run. Snapshot files
  stay on cluster scratch and never enter Git.
- `marangoni-multidrop.c` is the planar $n$-drop lattice at 64 points per
  radius with a $4R$ pitch; the box grows with the drop count.
- `marangoni-interact.c` is the planar eight-drop radial-$\sigma$ well.
  Default LEVEL 10 and $T_{\max}/t_0 = 12$. Not stock.
- `activity-drop.c` is the chemically fuelled drop solver, taken from
  `comphy-lab/active-drops-with-memory` `dropMove.c` at `45ce373`, with
  cluster dumps and a `--params` file parser. `activity-single.cfg` is one
  drop; `activity-seven.cfg` is seven custom centres in a $56R$ box. Its
  header is `src-local/activity.h`.
- Compile `marangoni-scale.c` and `marangoni-multidrop.c` with
  `-DUNIFORM=1` for the uniform-quadtree variants. Same TREE/MPI backend,
  `adapt_wavelet` off.

## Building

- Resolve `qcc` through `$BASILISK` or `command -v qcc`. Never hardcode a
  machine-local path.
- `qcc` rewrites included `.h` files next to the translation unit. Compile
  `activity-drop.c` only through `scripts/compile-activity-drop.sh` or in a
  throwaway directory holding a copy of `src-local/activity.h`. Never run
  `qcc simulationCases/activity-drop.c` from the repository root.
- `scripts/generate-sources.sh` emits every portable C99 file, including the
  2D and 3D Laplacian kernels and the uniform Marangoni variants, into
  `generated/`. That directory is ignored; the cluster compiles from it.

## Cluster sites

- Account codes, project and scratch roots and SSH aliases live in
  `site/mn5.env` and `site/snellius.env`, which are ignored by Git. The
  tracked `site/*.env.example` files document the variables. Never write a
  real account, username or absolute site path into a tracked file,
  including this one and the batch scripts.
- Every wrapper and helper does `source scripts/site-env.sh; site_env <site>`.
  The helper loads the site file, fails closed when `PROJECT_DST`,
  `SCRATCH_DST` or `SLURM_ACCOUNT` is missing, and fills
  `SITE_SBATCH_ARGS` with `--account`, `--output` and `--error`. Pass that
  array to every `sbatch` call. The `run*.sbatch` files carry no account or
  log path of their own and require `SCRATCH_DST` from the environment.
- `stage-*.sh` copies the compact tree, including `site/`, to `PROJECT_DST`
  and the generated C99 to `SCRATCH_DST`, so the same site file serves the
  cluster-side wrappers.
- Never compute on a login node. Login nodes compile, stage and submit.
- MareNostrum5 GPP: 112 cores per node, `--mem` refused. A sub-node job
  takes one exclusive node and `run.sbatch` launches `RANKS` ranks. Use the
  debug QoS only for a single compile-and-smoke job; scale-up runs on the
  project QoS.
- Snellius genoa: 192 cores per node, memory follows allocated cores. Pad
  `cpus-per-task` so a sub-node rank count still holds one node, and do not
  use `srun --exact` for the L14 or L9 kernels. Modules are `2024` and
  `OpenMPI/5.0.3-GCC-13.3.0`.

## Post-processing

- Use `publication-plots` for every figure, including diagnostic ones.
- Overlay the Curie and Occigen tables only when the mesh matches. The
  published Curie `mpi-circle` tables are full 2D grids with $2^{2L}$
  cells, not the adaptive mesh.
- `plot_field_frames.py` must sort frames by the parsed float snapshot time
  and stitch with sequential `%06d` image2 input (`-bf 0 -g 1`). Do not
  glob unpadded `t_*.png` names and do not use ffmpeg concat.
- The planar movie pipeline (`get_fields_planar.c`, `get_facets_planar.c`,
  `plot_field_frames.py`) and the axisymmetric extractors (`get_fields.c`,
  `get_facets.c`) are not interchangeable.
- Current campaign figures are `figures/laplacian-L9.pdf`,
  `figures/circle-L14.pdf`, `figures/circle-L12.pdf`,
  `figures/marangoni-uniform-per-iter.pdf`, `figures/planar-ndrop-per-iter.pdf`,
  `figures/marangoni-uniform-ndrop-per-iter.pdf` and
  `figures/marangoni-validate-vt-fields.pdf`. Update this list when a figure
  is added or retired.

## Hygiene

- Do not commit `basilisk/`, `.comphy-basilisk`, `.docker_mode`, generated
  C99, binaries, raw run output, snapshot files or `site/*.env`. Tracked
  outputs are the PDFs and CSV tables in `figures/`.
- `README.md` is public-facing. Keep job IDs, live timings, debugging notes
  and site-specific paths out of it; record them in your own project notes
  and move only settled results into the README.
- `CLAUDE.md` is local and ignored; it only points at this file.
