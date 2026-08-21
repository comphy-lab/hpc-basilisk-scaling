#!/usr/bin/env bash
# Copy compact scripts to Snellius project space and generated C99 to scratch.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SCRATCH_DST="${SCRATCH_DST:-/scratch-shared/your_user/hpc-basilisk-scaling}"
HOST="${HOST:-snellius}"

if [[ ! -f "${ROOT}/generated/_mpi-circle.c" || ! -f "${ROOT}/generated/_mpi-laplacian.c" || ! -f "${ROOT}/generated/_mpi-laplacian-2d.c" || ! -f "${ROOT}/generated/_marangoni-scale.c" || ! -f "${ROOT}/generated/_marangoni-multidrop.c" || ! -f "${ROOT}/generated/_marangoni-scale-uniform.c" || ! -f "${ROOT}/generated/_marangoni-multidrop-uniform.c" ]]; then
  echo "stage-snellius: run scripts/generate-sources.sh first" >&2
  exit 1
fi

ssh -o BatchMode=yes "${HOST}" "mkdir -p '${PROJECT_DST}' '${SCRATCH_DST}/generated' '${SCRATCH_DST}/bin' '${SCRATCH_DST}/runs'"

rsync -a --delete \
  --exclude '.git/' \
  --exclude 'generated/' \
  --exclude 'results/' \
  --exclude 'figures/' \
  --exclude '__pycache__/' \
  "${ROOT}/" "${HOST}:${PROJECT_DST}/"

rsync -a \
  "${ROOT}/generated/_mpi-circle.c" \
  "${ROOT}/generated/_mpi-laplacian.c" \
  "${ROOT}/generated/_mpi-laplacian-2d.c" \
  "${ROOT}/generated/_marangoni-scale.c" \
  "${ROOT}/generated/_marangoni-multidrop.c" \
  "${ROOT}/generated/_marangoni-scale-uniform.c" \
  "${ROOT}/generated/_marangoni-multidrop-uniform.c" \
  "${HOST}:${SCRATCH_DST}/generated/"

echo "staged scripts -> ${HOST}:${PROJECT_DST}"
echo "staged generated C99 -> ${HOST}:${SCRATCH_DST}/generated"
