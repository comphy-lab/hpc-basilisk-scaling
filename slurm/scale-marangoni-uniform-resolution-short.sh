#!/usr/bin/env bash
# Short-window uniform Marangoni rank sweep on MareNostrum5.
# TMAX/t0=0.05 for missing L12/L13 ranks; L11 n=2 keeps t/t0=0.5.
# TAG_OVERRIDE writes out-LEVEL-RANKS-t05 so t/t0=0.5 files stay intact.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
CORES_PER_NODE=112

submit() {
  local level="$1" ntasks="$2" tmax="$3" wall="$4" tag="$5" name="$6"
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local slurm_ntasks="${ntasks}"
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    slurm_ntasks="${CORES_PER_NODE}"
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="${name}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --exclusive \
    --time="${wall}" \
    --export=ALL,TEST=marangoni-scale-uniform,LEVEL="${level}",RANKS="${ntasks}",TMAX="${tmax}",TAG_OVERRIDE="${tag}" \
    "${SBATCH}"
}

echo "qos=${QOS} host=mn5 short-window TMAX/t0=0.05; L11 n=2 stays TMAX/t0=0.5"

echo -n "L11 n=2 t=0.5 wall=48h -> "
submit 11 2 0.5 "48:00:00" "11-2" "bsk-unif-11-2"

# L12: skip n=1,2 (n=2 still >72h even at t=0.05). Skip 512/1024 (already have t=0.5).
for spec in \
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
  submit 12 "${n}" 0.05 "${wall}" "12-${n}-t05" "bsk-unif-t05-12-${n}"
done

# L13: skip n<16. Include 512/1024 at short window (t=0.5 timed out).
for spec in \
  "16:72:00:00" \
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
  submit 13 "${n}" 0.05 "${wall}" "13-${n}-t05" "bsk-unif-t05-13-${n}"
done
