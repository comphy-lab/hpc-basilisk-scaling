#!/usr/bin/env bash
# Uniform-quadtree planar multi-drop Marangoni on MareNostrum5 GPP.
# Same 2-32 drops and ranks 4/16/64 as the adaptive sweep; 64 pts/R.
# Sub-node jobs take one exclusive GPP node (112 cores). run.sbatch
# launches RANKS MPI ranks, not SLURM_NTASKS.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
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
  local cores_per_node=112
  local nodes=1
  local slurm_ntasks="${cores_per_node}"
  local wall
  wall="$(wall_for "${ndrops}" "${ntasks}")"
  if [[ "${ntasks}" -ge "${cores_per_node}" ]]; then
    nodes=$(( (ntasks + cores_per_node - 1) / cores_per_node ))
    slurm_ntasks="${ntasks}"
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="bsk-unif-mdrop-${ndrops}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-multidrop-uniform,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "qos=${QOS} tmax/t0=${TMAX} grid=uniform"
for nd in ${DROPS_LIST}; do
  for n in ${RANKS_LIST}; do
    echo "ndrops=${nd} n=${n} -> $(submit "${nd}" "${n}")"
  done
done
