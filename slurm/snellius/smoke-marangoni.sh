#!/usr/bin/env bash
# Two-rank smoke of marangoni-scale on one exclusive genoa node.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"

sbatch --parsable \
  --job-name="snl-smoke-marangoni" \
  --partition=genoa \
  --nodes=1 \
  --ntasks=2 \
  --cpus-per-task=96 \
  --exclusive \
  --time=00:20:00 \
  --export=ALL,TEST=marangoni-scale,LEVEL=8,RANKS=2,TMAX=0.1 \
  "${SBATCH}"
