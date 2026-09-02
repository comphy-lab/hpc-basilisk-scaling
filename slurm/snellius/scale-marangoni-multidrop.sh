#!/usr/bin/env bash
# Planar multi-drop Marangoni on Snellius genoa: 2-32 drops, ranks 4,16,64.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
RANKS_LIST="${RANKS_LIST:-4 16 64}"
DROPS_LIST="${DROPS_LIST:-2 4 8 16 32}"
TMAX="${TMAX:-0.5}"

submit() {
  local ndrops="$1" ntasks="$2"
  local nodes=1
  local cpt=$(( CORES_PER_NODE / ntasks ))
  if [[ "${cpt}" -lt 1 ]]; then
    cpt=1
    nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="snl-mdrop-${ndrops}-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time=01:30:00 \
    --export=ALL,TEST=marangoni-multidrop,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} tmax/t0=${TMAX}"
for nd in ${DROPS_LIST}; do
  for n in ${RANKS_LIST}; do
    echo "ndrops=${nd} n=${n} -> $(submit "${nd}" "${n}")"
  done
done
