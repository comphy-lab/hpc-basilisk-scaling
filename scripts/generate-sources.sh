#!/usr/bin/env bash
# Emit portable C99 from the stock Basilisk tests. Requires qcc locally.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QCC="${QCC:-$(command -v qcc || true)}"
if [[ -z "${QCC}" ]]; then
  echo "generate-sources: qcc not found; set QCC or PATH" >&2
  exit 1
fi
export BASILISK="${BASILISK:-$(cd "$(dirname "${QCC}")" && pwd)}"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/mn5-basilisk-src.XXXXXX")"
cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

cp "${ROOT}/simulationCases/mpi-circle.c" \
   "${ROOT}/simulationCases/mpi-laplacian.c" \
   "${ROOT}/simulationCases/check_restriction.h" \
   "${WORKDIR}/"

mkdir -p "${ROOT}/generated"
(
  cd "${WORKDIR}"
  "${QCC}" -source -D_MPI=1 mpi-circle.c
  "${QCC}" -grid=octree -source -D_MPI=1 mpi-laplacian.c
  mv _mpi-laplacian.c _mpi-laplacian-3d.c
  "${QCC}" -source -D_MPI=1 mpi-laplacian.c
  mv _mpi-laplacian.c _mpi-laplacian-2d.c
  mv _mpi-laplacian-3d.c _mpi-laplacian.c
)

install -m 0644 "${WORKDIR}/_mpi-circle.c" "${ROOT}/generated/_mpi-circle.c"
install -m 0644 "${WORKDIR}/_mpi-laplacian.c" "${ROOT}/generated/_mpi-laplacian.c"
install -m 0644 "${WORKDIR}/_mpi-laplacian-2d.c" "${ROOT}/generated/_mpi-laplacian-2d.c"
echo "wrote ${ROOT}/generated/_mpi-circle.c"
echo "wrote ${ROOT}/generated/_mpi-laplacian.c"
echo "wrote ${ROOT}/generated/_mpi-laplacian-2d.c"
echo "qcc=${QCC}"
echo "BASILISK=${BASILISK}"
