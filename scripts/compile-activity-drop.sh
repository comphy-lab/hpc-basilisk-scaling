#!/usr/bin/env bash
# Compile activity-drop.c in a throwaway directory. qcc rewrites included
# headers next to the source; never point it at the tracked src-local copy.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QCC="${QCC:-$(command -v qcc || true)}"
if [[ -z "${QCC}" ]]; then
  echo "compile-activity-drop: qcc not found; set QCC or PATH" >&2
  exit 1
fi
export BASILISK="${BASILISK:-$(cd "$(dirname "${QCC}")" && pwd)}"

OUT="${1:-${ROOT}/activity-drop}"
if [[ "${OUT}" != /* ]]; then
  OUT="$(pwd)/${OUT}"
fi
mkdir -p "$(dirname "${OUT}")"
WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/activity-drop-build.XXXXXX")"
cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

mkdir -p "${WORKDIR}/src-local"
cp "${ROOT}/simulationCases/activity-drop.c" "${WORKDIR}/"
cp "${ROOT}/src-local/activity.h" "${WORKDIR}/src-local/"

CC99="${CC99:-}"
(
  cd "${WORKDIR}"
  if [[ -n "${CC99}" ]]; then
    export CC99
    "${QCC}" -Wall -O2 -D_MPI=1 -disable-dimensions \
      activity-drop.c -o "${OUT}" -lm
  else
    "${QCC}" -Wall -O2 -disable-dimensions \
      activity-drop.c -o "${OUT}" -lm
  fi
)
echo "compiled ${OUT}"
echo "qcc=${QCC}"
echo "BASILISK=${BASILISK}"
