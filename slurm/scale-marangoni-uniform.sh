#!/usr/bin/env bash
# Uniform-quadtree marangoni-scale on MareNostrum5 GPP.
# LEVEL 10 only (1024^2 cells). L12 uniform is 4096^2 and is not this sweep.
# Rank list is powers of two. Sub-node jobs take a full GPP node (112
# cores, 2 GB/core) because BSC forbids --mem. run.sbatch launches
# RANKS MPI ranks, not SLURM_NTASKS.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
RANKS_LIST="${RANKS_LIST:-2 4 8 16 32 64 128 256 512 1024 2048 4096}"
LEVELS="${LEVELS:-10}"
TMAX="${TMAX:-0.5}"

wall_for() {
  local ntasks="$1"
  if [[ "${ntasks}" -le 16 ]]; then
    echo "04:00:00"
  elif [[ "${ntasks}" -le 64 ]]; then
    echo "02:00:00"
  else
    echo "01:00:00"
  fi
}

submit() {
  local level="$1" ntasks="$2"
  local cores_per_node=112
  local nodes=$(( (ntasks + cores_per_node - 1) / cores_per_node ))
  local slurm_ntasks="${ntasks}"
  local wall
  wall="$(wall_for "${ntasks}")"
  if [[ "${ntasks}" -lt "${cores_per_node}" ]]; then
    nodes=1
    slurm_ntasks="${cores_per_node}"
  fi
  sbatch --parsable \
    --job-name="bsk-unif-${level}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale-uniform,LEVEL="${level}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "qos=${QOS} tmax/t0=${TMAX} levels=${LEVELS} grid=uniform"
for level in ${LEVELS}; do
  for n in ${RANKS_LIST}; do
    echo "marangoni-uniform L=${level} n=${n} -> $(submit "${level}" "${n}")"
  done
done
