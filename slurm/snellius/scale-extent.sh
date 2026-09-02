#!/usr/bin/env bash
# Official Curie/Occigen rank list on Snellius genoa.
# Same tests as slurm/scale-extent.sh: 2D full-grid L=12/14 and 3D L=9.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run.sbatch"
PARTITION="${PARTITION:-genoa}"
CORES_PER_NODE="${CORES_PER_NODE:-192}"
RANKS_LIST="${RANKS_LIST:-1 2 4 8 16 32 64 128 256 512 1024 2048 4096 8192 16384}"

submit() {
  local test="$1" level="$2" ntasks="$3"
  local nodes=$(( (ntasks + CORES_PER_NODE - 1) / CORES_PER_NODE ))
  local cpt=1
  # Snellius bills ~1.75 GB/core. srun --exact shrinks the memory
  # cgroup to the launched rank count, which OOMs L=14/L=9. Pad
  # cpus-per-task so a sub-node rank count still occupies one genoa
  # node (192 cores, 336 GB).
  if [[ "${ntasks}" -lt "${CORES_PER_NODE}" ]]; then
    nodes=1
    cpt=$(( CORES_PER_NODE / ntasks ))
    if [[ "${cpt}" -lt 1 ]]; then
      cpt=1
    fi
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="snl-${test}-${level}-${ntasks}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --cpus-per-task="${cpt}" \
    --exclusive \
    --time=00:45:00 \
    --export=ALL,TEST="${test}",LEVEL="${level}",RANKS="${ntasks}" \
    "${SBATCH}"
}

echo "partition=${PARTITION} cores_per_node=${CORES_PER_NODE}"
for n in ${RANKS_LIST}; do
  if [[ "${n}" -ge 4 ]]; then
    job_id="$(submit mpi-laplacian-2d 14 "${n}")"
    echo "2d L=14 n=${n} -> ${job_id}"
  fi
  if [[ "${n}" -ge 2 ]]; then
    job_id="$(submit mpi-laplacian-2d 12 "${n}")"
    echo "2d L=12 n=${n} -> ${job_id}"
    job_id="$(submit mpi-laplacian 9 "${n}")"
    echo "3d L=9 n=${n} -> ${job_id}"
  fi
done
