#!/usr/bin/env bash
# Two-rank then one-node smoke of marangoni-scale on gp_debug.
# LEVEL 8 (16 points per radius) and a short TMAX, not the scaling grid.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"

submit() {
  local ntasks="$1" nodes="$2" slurm_ntasks="$3"
  sbatch --parsable \
    --job-name="smoke-marangoni-${ntasks}" \
    --qos=gp_debug \
    --ntasks="${slurm_ntasks}" \
    --nodes="${nodes}" \
    --exclusive \
    --time=00:20:00 \
    --export=ALL,TEST=marangoni-scale,LEVEL=8,RANKS="${ntasks}",TMAX=0.1 \
    "${SBATCH}"
}

echo "submitting marangoni smoke"
echo "2 ranks (full node pad) -> $(submit 2 1 112)"
echo "1 node 112 ranks -> $(submit 112 1 112)"
