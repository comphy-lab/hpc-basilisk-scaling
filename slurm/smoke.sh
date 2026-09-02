#!/usr/bin/env bash
# Two-rank then one-node smoke for both stock tests on gp_debug.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"

submit() {
  local test="$1" ntasks="$2" nodes="$3" level="$4"
  local extra=()
  if [[ "${nodes}" -gt 1 ]]; then
    extra+=(--nodes="${nodes}")
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="smoke-${test}-${ntasks}" \
    --ntasks="${ntasks}" \
    --nodes="${nodes}" \
    --dependency=singleton \
    --export=ALL,TEST="${test}",LEVEL="${level}" \
    "${extra[@]}" \
    "${SBATCH}"
}

echo "submitting smoke jobs"
jid1="$(submit mpi-circle 2 1 8)"
echo "mpi-circle 2 ranks -> ${jid1}"
jid2="$(submit mpi-laplacian 2 1 6)"
echo "mpi-laplacian 2 ranks -> ${jid2}"
jid3="$(submit mpi-circle 112 1 10)"
echo "mpi-circle 1 node -> ${jid3}"
jid4="$(submit mpi-laplacian 112 1 7)"
echo "mpi-laplacian 1 node -> ${jid4}"
echo "${jid1} ${jid2} ${jid3} ${jid4}"
