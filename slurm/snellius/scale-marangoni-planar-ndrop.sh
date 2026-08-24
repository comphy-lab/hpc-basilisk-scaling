#!/usr/bin/env bash
# Planar uniform Marangoni rank sweep: 1,2,8,32 drops at 64 pts/R.
# TMAX/t0=0.05, ranks 2..256. n=1 skipped. 1/2/8 drops stay LEVEL 10;
# 32 drops grow the box to LEVEL 11.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
TMAX="${TMAX:-0.05}"
DROPS_LIST="${DROPS_LIST:-1 2 8 32}"

wall_for() {
  local ndrops="$1" ntasks="$2"
  if [[ "${ndrops}" -ge 32 ]]; then
    case "${ntasks}" in
      2) echo "08:00:00" ;;
      4|8) echo "04:00:00" ;;
      16|32) echo "02:00:00" ;;
      *) echo "01:00:00" ;;
    esac
  else
    case "${ntasks}" in
      2) echo "02:00:00" ;;
      4|8) echo "01:00:00" ;;
      16|32) echo "00:30:00" ;;
      *) echo "00:20:00" ;;
    esac
  fi
}

submit() {
  local ndrops="$1" ntasks="$2"
  local wall
  wall="$(wall_for "${ndrops}" "${ntasks}")"
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local cpt=1
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    cpt=$(( CORES_PER_NODE / ntasks ))
    if [[ "${cpt}" -lt 1 ]]; then
      cpt=1
    fi
  fi
  sbatch --parsable \
    --job-name="snl-p${ndrops}d-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-multidrop-uniform,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}",TAG_OVERRIDE="${ndrops}-${ntasks}-t05" \
    "${SBATCH}"
}

echo "partition=${PARTITION} host=snellius planar uniform 64 pts/R TMAX/t0=${TMAX} drops=${DROPS_LIST}"
for nd in ${DROPS_LIST}; do
  for n in 2 4 8 16 32 64 128 256; do
    echo -n "ndrops=${nd} n=${n} wall=$(wall_for "${nd}" "${n}") -> "
    submit "${nd}" "${n}"
  done
done
