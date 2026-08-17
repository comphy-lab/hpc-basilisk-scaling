#!/usr/bin/env bash
# Pull MN5 timer tables into a local results tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH_DST="${SCRATCH_DST:-/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling}"
TRANSFER="${TRANSFER:-mn5-transfer}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%MZ)}"
DEST="${ROOT}/results/${STAMP}"

mkdir -p "${DEST}"
rsync -a "${TRANSFER}:${SCRATCH_DST}/runs/" "${DEST}/"
ln -sfn "${STAMP}" "${ROOT}/results/latest"
echo "collected ${DEST}"
find "${DEST}" -name 'out-*' | sort
