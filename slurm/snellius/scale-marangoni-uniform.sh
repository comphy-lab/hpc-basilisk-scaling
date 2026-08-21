#!/usr/bin/env bash
# Uniform-quadtree marangoni-scale on Snellius genoa.
# LEVEL 10 only (1024^2 cells). L12 uniform is not this sweep.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
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
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local cpt=1
  local wall
  wall="$(wall_for "${ntasks}")"
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    cpt=$(( CORES_PER_NODE / ntasks ))
    if [[ "${cpt}" -lt 1 ]]; then
      cpt=1
    fi
  fi
  sbatch --parsable \
    --job-name="snl-unif-${level}-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale-uniform,LEVEL="${level}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} tmax/t0=${TMAX} levels=${LEVELS} grid=uniform"
for level in ${LEVELS}; do
  for n in ${RANKS_LIST}; do
    echo "marangoni-uniform L=${level} n=${n} -> $(submit "${level}" "${n}")"
  done
done
