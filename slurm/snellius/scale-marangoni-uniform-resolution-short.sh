#!/usr/bin/env bash
# Short-window uniform Marangoni rank sweep on Snellius genoa.
# TMAX/t0=0.05 for missing L12/L13 ranks; L11 n=2 keeps t/t0=0.5.
# TAG_OVERRIDE writes out-LEVEL-RANKS-t05 so t/t0=0.5 files stay intact.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"

submit() {
  local level="$1" ntasks="$2" tmax="$3" wall="$4" tag="$5" name="$6"
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
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="${name}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale-uniform,LEVEL="${level}",RANKS="${ntasks}",TMAX="${tmax}",TAG_OVERRIDE="${tag}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} host=snellius short-window TMAX/t0=0.05; L11 n=2 stays TMAX/t0=0.5"

echo -n "L11 n=2 t=0.5 wall=48h -> "
submit 11 2 0.5 "48:00:00" "11-2" "snl-unif-11-2"

# L12 n=2 is ~70h at t=0.05; 5-day cap is enough.
for spec in \
  "2:5-00:00:00" \
  "4:72:00:00" \
  "8:72:00:00" \
  "16:36:00:00" \
  "32:24:00:00" \
  "64:12:00:00" \
  "128:06:00:00" \
  "256:03:00:00"
do
  n="${spec%%:*}"
  wall="${spec#*:}"
  echo -n "L12 n=${n} t=0.05 wall=${wall} -> "
  submit 12 "${n}" 0.05 "${wall}" "12-${n}-t05" "snl-unif-t05-12-${n}"
done

for spec in \
  "16:5-00:00:00" \
  "32:72:00:00" \
  "64:36:00:00" \
  "128:24:00:00" \
  "256:12:00:00" \
  "512:06:00:00" \
  "1024:03:00:00"
do
  n="${spec%%:*}"
  wall="${spec#*:}"
  echo -n "L13 n=${n} t=0.05 wall=${wall} -> "
  submit 13 "${n}" 0.05 "${wall}" "13-${n}-t05" "snl-unif-t05-13-${n}"
done
