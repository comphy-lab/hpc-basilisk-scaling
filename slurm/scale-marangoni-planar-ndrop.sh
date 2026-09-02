#!/usr/bin/env bash
# Planar uniform Marangoni rank sweep: 1,2,8,32 drops at 64 pts/R.
# TMAX/t0=0.05, ranks 2..256. n=1 skipped. 1/2/8 drops stay LEVEL 10;
# 32 drops grow the box to LEVEL 11.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
CORES_PER_NODE=112
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
  local slurm_ntasks="${ntasks}"
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    slurm_ntasks="${CORES_PER_NODE}"
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="bsk-p${ndrops}d-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-multidrop-uniform,NDROPS="${ndrops}",RANKS="${ntasks}",TMAX="${TMAX}",TAG_OVERRIDE="${ndrops}-${ntasks}-t05" \
    "${SBATCH}"
}

echo "qos=${QOS} host=mn5 planar uniform 64 pts/R TMAX/t0=${TMAX} drops=${DROPS_LIST}"
for nd in ${DROPS_LIST}; do
  for n in 2 4 8 16 32 64 128 256; do
    echo -n "ndrops=${nd} n=${n} wall=$(wall_for "${nd}" "${n}") -> "
    submit "${nd}" "${n}"
  done
done
