#!/usr/bin/env bash
# Uniform axi Marangoni resolution sweep on MareNostrum5 GPP.
# pts/R = 2^(LEVEL-4) on the 16R box: 64,128,256,512 -> LEVEL 10-13.
# L10 ranks 2-4096 are submitted by scale-marangoni-uniform.sh.
# Sub-node jobs pad to 112 tasks; srun uses RANKS.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
TMAX="${TMAX:-0.5}"
CORES_PER_NODE=112

# LEVEL:ranks. Skip ranks whose estimated wall exceeds gp_ehpc (3 days).
PAIRS=(
  "10:1"
  "11:1 2 4 8 16 32 64 128 256 512 1024"
  "12:4 8 16 32 64 128 256 512 1024"
  "13:32 64 128 256 512 1024"
)

wall_for() {
  local level="$1" ntasks="$2"
  case "${level}" in
    10)
      echo "08:00:00"
      ;;
    11)
      if [[ "${ntasks}" -le 1 ]]; then echo "24:00:00"
      elif [[ "${ntasks}" -le 2 ]]; then echo "16:00:00"
      elif [[ "${ntasks}" -le 8 ]]; then echo "08:00:00"
      elif [[ "${ntasks}" -le 32 ]]; then echo "04:00:00"
      else echo "02:00:00"
      fi
      ;;
    12)
      if [[ "${ntasks}" -le 4 ]]; then echo "48:00:00"
      elif [[ "${ntasks}" -le 8 ]]; then echo "24:00:00"
      elif [[ "${ntasks}" -le 32 ]]; then echo "12:00:00"
      else echo "04:00:00"
      fi
      ;;
    13)
      if [[ "${ntasks}" -le 32 ]]; then echo "48:00:00"
      elif [[ "${ntasks}" -le 64 ]]; then echo "24:00:00"
      elif [[ "${ntasks}" -le 256 ]]; then echo "08:00:00"
      else echo "04:00:00"
      fi
      ;;
    *)
      echo "04:00:00"
      ;;
  esac
}

submit() {
  local level="$1" ntasks="$2"
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local slurm_ntasks="${ntasks}"
  local wall
  wall="$(wall_for "${level}" "${ntasks}")"
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    slurm_ntasks="${CORES_PER_NODE}"
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="bsk-unif-${level}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale-uniform,LEVEL="${level}",RANKS="${ntasks}",TMAX="${TMAX}" \
    "${SBATCH}"
}

echo "qos=${QOS} tmax/t0=${TMAX} grid=uniform host=mn5"
echo "skip L12 n=1,2 and L13 n<32: 3-day gp_ehpc cap at t/t0=0.5"
for pair in "${PAIRS[@]}"; do
  level="${pair%%:*}"
  ranks="${pair#*:}"
  pts=$(( 1 << (level - 4) ))
  for n in ${ranks}; do
    echo "pts/R=${pts} L=${level} n=${n} wall=$(wall_for "${level}" "${n}") -> $(submit "${level}" "${n}")"
  done
done
