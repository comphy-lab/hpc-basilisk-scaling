#!/usr/bin/env bash
# Submit the official Curie/Occigen rank list on gp_ehpc.
# 2D full-grid mpi-laplacian matches the published Curie tables
# (2^{2L} cells). 3D octree matches Occigen.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
RANKS_LIST="${RANKS_LIST:-1 2 4 8 16 32 64 128 256 512 1024 2048 4096 8192 16384}"

submit() {
  local test="$1" level="$2" ntasks="$3"
  local nodes=$(( (ntasks + 111) / 112 ))
  if [[ "${nodes}" -lt 1 ]]; then
    nodes=1
  fi
  sbatch --parsable \
    --job-name="bsk-${test}-${level}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --time=00:45:00 \
    --export=ALL,TEST="${test}",LEVEL="${level}" \
    "${SBATCH}"
}

# Stock mpi-laplacian aborts if the built-in 1e6 cells/s estimate exceeds 100 s.
# L=14 2D (2^28 cells) therefore starts at 4 ranks; L=9 3D at 2 ranks.
echo "qos=${QOS}"
for n in ${RANKS_LIST}; do
  if [[ "${n}" -ge 4 ]]; then
    echo "2d L=14 n=${n} -> $(submit mpi-laplacian-2d 14 "${n}")"
  fi
  echo "2d L=12 n=${n} -> $(submit mpi-laplacian-2d 12 "${n}")"
  if [[ "${n}" -ge 2 ]]; then
    echo "3d L=9 n=${n} -> $(submit mpi-laplacian 9 "${n}")"
  fi
done
