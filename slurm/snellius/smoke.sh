#!/usr/bin/env bash
# Two-rank smoke on one exclusive genoa node. Do not run on a login node.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"

submit() {
  local test="$1" level="$2"
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="snl-smoke-${test}" \
    --partition=genoa \
    --nodes=1 \
    --ntasks=2 \
    --cpus-per-task=96 \
    --exclusive \
    --time=00:15:00 \
    --export=ALL,TEST="${test}",LEVEL="${level}",RANKS=2 \
    "${SBATCH}"
}

job_id="$(submit mpi-laplacian-2d 8)"
echo "2d L=8 n=2 -> ${job_id}"
job_id="$(submit mpi-laplacian 6)"
echo "3d L=6 n=2 -> ${job_id}"
