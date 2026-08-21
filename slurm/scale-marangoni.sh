#!/usr/bin/env bash
# Strong-scaling sweep of stock marangoni.c physics on MareNostrum5 GPP.
# Rank list is powers of two. Sub-node jobs take a full GPP node (112
# cores, 2 GB/core) because BSC forbids --mem.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
RANKS_LIST="${RANKS_LIST:-2 4 8 16 32 64 128 256 512 1024 2048 4096}"
LEVELS="${LEVELS:-10 12}"
TMAX="${TMAX:-0.5}"

submit() {
  local level="$1" ntasks="$2"
  local cores_per_node=112
  local nodes=$(( (ntasks + cores_per_node - 1) / cores_per_node ))
  local slurm_ntasks="${ntasks}"
  local wall="01:00:00"
  if [[ "${ntasks}" -lt "${cores_per_node}" ]]; then
    nodes=1
    slurm_ntasks="${cores_per_node}"
  fi
  if [[ "${level}" -ge 12 && "${ntasks}" -le 16 ]]; then
    wall="02:00:00"
  fi
  sbatch --parsable \
    --job-name="bsk-marangoni-${level}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale,LEVEL="${level}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "qos=${QOS} tmax/t0=${TMAX} levels=${LEVELS}"
for level in ${LEVELS}; do
  for n in ${RANKS_LIST}; do
    echo "marangoni L=${level} n=${n} nodes=ceil -> $(submit "${level}" "${n}")"
  done
done
