#!/usr/bin/env bash
# Uniform-quadtree planar multi-drop Marangoni on Snellius genoa.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
RANKS_LIST="${RANKS_LIST:-4 16 64}"
DROPS_LIST="${DROPS_LIST:-2 4 8 16 32}"
TMAX="${TMAX:-0.5}"

wall_for() {
  local ndrops="$1" ntasks="$2"
  if [[ "${ndrops}" -ge 16 && "${ntasks}" -le 4 ]]; then
    echo "48:00:00"
  elif [[ "${ndrops}" -ge 16 && "${ntasks}" -le 16 ]]; then
    echo "12:00:00"
  elif [[ "${ntasks}" -le 16 ]]; then
    echo "04:00:00"
  else
    echo "02:00:00"
  fi
}

submit() {
  local ndrops="$1" ntasks="$2"
  local nodes=1
  local cpt=$(( CORES_PER_NODE / ntasks ))
  local wall
  wall="$(wall_for "${ndrops}" "${ntasks}")"
  if [[ "${cpt}" -lt 1 ]]; then
    cpt=1
    nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  fi
  sbatch --parsable \
    --job-name="snl-unif-mdrop-${ndrops}-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-multidrop-uniform,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} tmax/t0=${TMAX} grid=uniform"
for nd in ${DROPS_LIST}; do
  for n in ${RANKS_LIST}; do
    echo "ndrops=${nd} n=${n} -> $(submit "${nd}" "${n}")"
  done
done
