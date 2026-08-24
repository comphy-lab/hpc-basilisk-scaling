#!/usr/bin/env bash
# Uniform axi Marangoni resolution sweep on Snellius genoa.
# pts/R = 2^(LEVEL-4) on the 16R box: 64,128,256,512 -> LEVEL 10-13.
# L10 ranks 2-4096 are submitted by scale-marangoni-uniform.sh.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
TMAX="${TMAX:-0.5}"

# Snellius genoa allows 5 days. Still skip n=1 at L12/L13 and n<16 at L13.
PAIRS=(
  "10:1"
  "11:1 2 4 8 16 32 64 128 256 512 1024"
  "12:2 4 8 16 32 64 128 256 512 1024"
  "13:16 32 64 128 256 512 1024"
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
      if [[ "${ntasks}" -le 2 ]]; then echo "5-00:00:00"
      elif [[ "${ntasks}" -le 4 ]]; then echo "48:00:00"
      elif [[ "${ntasks}" -le 8 ]]; then echo "24:00:00"
      elif [[ "${ntasks}" -le 32 ]]; then echo "12:00:00"
      else echo "04:00:00"
      fi
      ;;
    13)
      if [[ "${ntasks}" -le 16 ]]; then echo "5-00:00:00"
      elif [[ "${ntasks}" -le 32 ]]; then echo "48:00:00"
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
  local cpt=1
  local wall
  wall="$(wall_for "${level}" "${ntasks}")"
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

echo "partition=${PARTITION} tmax/t0=${TMAX} grid=uniform host=snellius"
echo "skip L12 n=1 and L13 n<16: 5-day cap at t/t0=0.5"
for pair in "${PAIRS[@]}"; do
  level="${pair%%:*}"
  ranks="${pair#*:}"
  pts=$(( 1 << (level - 4) ))
  for n in ${ranks}; do
    echo "pts/R=${pts} L=${level} n=${n} wall=$(wall_for "${level}" "${n}") -> $(submit "${level}" "${n}")"
  done
done
