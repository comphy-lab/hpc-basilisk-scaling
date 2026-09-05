#!/usr/bin/env bash
# Copy compact scripts to Snellius project space and generated C99 to scratch.
# Reads site/snellius.env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/site-env.sh
source "${ROOT}/scripts/site-env.sh"
site_env snellius
HOST="${HOST:?set HOST (login SSH alias) in site/snellius.env}"

need=(
  _mpi-circle.c
  _mpi-laplacian.c
  _mpi-laplacian-2d.c
  _marangoni-scale.c
  _marangoni-multidrop.c
  _marangoni-scale-uniform.c
  _marangoni-multidrop-uniform.c
  _marangoni-interact.c
  _activity-drop.c
  _bursting-uniform-init.c
  _bursting-uniform.c
  _taylorculick-uniform.c
  _ve3d-impact-uniform.c
  _drop-impact-uniform.c
  _jumping-uniform-init.c
  _jumping-uniform.c
)
for f in "${need[@]}"; do
  if [[ ! -f "${ROOT}/generated/${f}" ]]; then
    echo "stage-snellius: run scripts/generate-sources.sh first (missing ${f})" >&2
    exit 1
  fi
done

ssh -o BatchMode=yes "${HOST}" "mkdir -p '${PROJECT_DST}' '${SCRATCH_DST}/generated' '${SCRATCH_DST}/bin' '${SCRATCH_DST}/runs'"

rsync -a --delete \
  --exclude '.git/' \
  --exclude 'generated/' \
  --exclude 'results/' \
  --exclude 'figures/' \
  --exclude '__pycache__/' \
  --exclude 'bin/' \
  --exclude 'runs/' \
  "${ROOT}/" "${HOST}:${PROJECT_DST}/"

# shellcheck disable=SC2086
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
  "${ROOT}/generated/_bursting-uniform-init.c" \
  "${ROOT}/generated/_bursting-uniform.c" \
  "${ROOT}/generated/_taylorculick-uniform.c" \
  "${ROOT}/generated/_ve3d-impact-uniform.c" \
  "${ROOT}/generated/_drop-impact-uniform.c" \
  "${ROOT}/generated/_jumping-uniform-init.c" \
  "${ROOT}/generated/_jumping-uniform.c" \
  "${HOST}:${SCRATCH_DST}/generated/"

echo "staged scripts -> ${HOST}:${PROJECT_DST}"
echo "staged generated C99 -> ${HOST}:${SCRATCH_DST}/generated"
