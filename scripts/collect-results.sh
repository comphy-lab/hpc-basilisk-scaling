#!/usr/bin/env bash
# Pull MareNostrum5 timer tables into a local results tree. Reads site/mn5.env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=scripts/site-env.sh
source "${ROOT}/scripts/site-env.sh"
site_env mn5
TRANSFER="${TRANSFER:?set TRANSFER (data-transfer SSH alias) in site/mn5.env}"
STAMP="${STAMP:-$(date -u +%Y%m%dT%H%MZ)}"
DEST="${ROOT}/results/${STAMP}"

mkdir -p "${DEST}"
rsync -a "${TRANSFER}:${SCRATCH_DST}/runs/" "${DEST}/"
ln -sfn "${STAMP}" "${ROOT}/results/latest"
echo "collected ${DEST}"
find "${DEST}" -name 'out-*' | sort
