#!/usr/bin/env bash
# Pull Snellius timer tables into a local results tree. Reads site/snellius.env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/site-env.sh
source "${ROOT}/scripts/site-env.sh"
site_env snellius
HOST="${HOST:?set HOST (login SSH alias) in site/snellius.env}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%MZ)}"
DEST="${ROOT}/results/snellius/${STAMP}"

mkdir -p "${DEST}"
rsync -a "${HOST}:${SCRATCH_DST}/runs/" "${DEST}/"
ln -sfn "${STAMP}" "${ROOT}/results/snellius/latest"
echo "collected ${DEST}"
find "${DEST}" -name 'out-*' | sort
