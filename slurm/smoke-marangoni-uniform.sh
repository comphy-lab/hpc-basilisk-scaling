#!/usr/bin/env bash
# Two-rank uniform-quadtree smoke of marangoni-scale on gp_debug.
# LEVEL 8 is 256^2 cells; short TMAX, not the scaling grid.
# --ntasks=112 pads the exclusive GPP node; RANKS=2 is the MPI size.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"

sbatch --parsable \
  --job-name="smoke-unif-marangoni" \
  --qos=gp_debug \
  --ntasks=112 \
  --nodes=1 \
  --exclusive \
  --time=00:20:00 \
  --export=ALL,TEST=marangoni-scale-uniform,LEVEL=8,RANKS=2,TMAX=0.1 \
  "${SBATCH}"
