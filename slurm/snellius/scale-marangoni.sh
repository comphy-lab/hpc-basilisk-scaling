#!/usr/bin/env bash
# Strong-scaling sweep of stock marangoni.c physics on Snellius genoa.
# Sub-node jobs pad cpus-per-task so one genoa node (192 cores, 336 GB)
# stays allocated. Do not use srun --exact.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
RANKS_LIST="${RANKS_LIST:-2 4 8 16 32 64 128 256 512 1024 2048 4096}"
LEVELS="${LEVELS:-10 12}"
TMAX="${TMAX:-0.5}"

submit() {
  local level="$1" ntasks="$2"
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local cpt=1
  local wall="01:00:00"
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    cpt=$(( CORES_PER_NODE / ntasks ))
    if [[ "${cpt}" -lt 1 ]]; then
      cpt=1
    fi
  fi
  if [[ "${level}" -ge 12 && "${ntasks}" -le 16 ]]; then
    wall="02:00:00"
  fi
  sbatch --parsable \
    --job-name="snl-marangoni-${level}-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale,LEVEL="${level}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} tmax/t0=${TMAX} levels=${LEVELS}"
for level in ${LEVELS}; do
  for n in ${RANKS_LIST}; do
    echo "marangoni L=${level} n=${n} -> $(submit "${level}" "${n}")"
  done
done
