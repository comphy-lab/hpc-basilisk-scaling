#!/usr/bin/env bash
# Copy compact scripts/sources to MN5 project space and generated C99 to scratch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SCRATCH_DST="${SCRATCH_DST:-/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling}"
TRANSFER="${TRANSFER:-mn5-transfer}"

if [[ ! -f "${ROOT}/generated/_mpi-circle.c" || ! -f "${ROOT}/generated/_mpi-laplacian.c" || ! -f "${ROOT}/generated/_mpi-laplacian-2d.c" || ! -f "${ROOT}/generated/_marangoni-scale.c" || ! -f "${ROOT}/generated/_marangoni-multidrop.c" || ! -f "${ROOT}/generated/_marangoni-scale-uniform.c" || ! -f "${ROOT}/generated/_marangoni-multidrop-uniform.c" || ! -f "${ROOT}/generated/_marangoni-interact.c" || ! -f "${ROOT}/generated/_activity-drop.c" ]]; then
  echo "stage-mn5: run scripts/generate-sources.sh first" >&2
  exit 1
fi

ssh -o BatchMode=yes "${TRANSFER}" "mkdir -p '${PROJECT_DST}' '${SCRATCH_DST}/generated' '${SCRATCH_DST}/bin' '${SCRATCH_DST}/runs'"

rsync -a --delete \
  --exclude '.git/' \
  --exclude 'generated/' \
  --exclude 'results/' \
  --exclude 'figures/' \
  --exclude '__pycache__/' \
  "${ROOT}/" "${TRANSFER}:${PROJECT_DST}/"

rsync -a \
  "${ROOT}/generated/_mpi-circle.c" \
  "${ROOT}/generated/_mpi-laplacian.c" \
  "${ROOT}/generated/_mpi-laplacian-2d.c" \
  "${ROOT}/generated/_marangoni-scale.c" \
  "${ROOT}/generated/_marangoni-multidrop.c" \
  "${ROOT}/generated/_marangoni-scale-uniform.c" \
  "${ROOT}/generated/_marangoni-multidrop-uniform.c" \
  "${ROOT}/generated/_marangoni-interact.c" \
  "${ROOT}/generated/_activity-drop.c" \
  "${TRANSFER}:${SCRATCH_DST}/generated/"

echo "staged scripts -> ${TRANSFER}:${PROJECT_DST}"
echo "staged generated C99 -> ${TRANSFER}:${SCRATCH_DST}/generated"
