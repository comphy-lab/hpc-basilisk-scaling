#!/usr/bin/env bash
# Planar multi-drop Marangoni: 2,4,8,16,32 drops at 64 pts/R, ranks 4,16,64.
# Sub-node jobs take one exclusive GPP node (112 cores).
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
RANKS_LIST="${RANKS_LIST:-4 16 64}"
DROPS_LIST="${DROPS_LIST:-2 4 8 16 32}"
TMAX="${TMAX:-0.5}"

submit() {
  local ndrops="$1" ntasks="$2"
  local cores_per_node=112
  local nodes=1
  local slurm_ntasks="${cores_per_node}"
  if [[ "${ntasks}" -ge "${cores_per_node}" ]]; then
    nodes=$(( (ntasks + cores_per_node - 1) / cores_per_node ))
    slurm_ntasks="${ntasks}"
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="bsk-mdrop-${ndrops}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time=01:30:00 \
    --export=ALL,TEST=marangoni-multidrop,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "qos=${QOS} tmax/t0=${TMAX}"
for nd in ${DROPS_LIST}; do
  for n in ${RANKS_LIST}; do
    echo "ndrops=${nd} n=${n} -> $(submit "${nd}" "${n}")"
  done
done
