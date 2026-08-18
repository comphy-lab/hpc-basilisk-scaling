#!/usr/bin/env bash
# Pull Snellius timer tables into a local results tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH_DST="${SCRATCH_DST:-/scratch-shared/your_user/hpc-basilisk-scaling}"
HOST="${HOST:-snellius}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%MZ)}"
DEST="${ROOT}/results/snellius/${STAMP}"

mkdir -p "${DEST}"
rsync -a "${HOST}:${SCRATCH_DST}/runs/" "${DEST}/"
ln -sfn "${STAMP}" "${ROOT}/results/snellius/latest"
echo "collected ${DEST}"
find "${DEST}" -name 'out-*' | sort
