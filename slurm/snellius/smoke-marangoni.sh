#!/usr/bin/env bash
# Two-rank smoke of marangoni-scale on one exclusive genoa node.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"

sbatch --parsable \
  "${SITE_SBATCH_ARGS[@]}" \
  --job-name="snl-smoke-marangoni" \
  --partition=genoa \
  --nodes=1 \
  --ntasks=2 \
  --cpus-per-task=96 \
  --exclusive \
  --time=00:20:00 \
  --export=ALL,TEST=marangoni-scale,LEVEL=8,RANKS=2,TMAX=0.1 \
  "${SBATCH}"
