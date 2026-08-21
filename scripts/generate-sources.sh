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
   "${ROOT}/simulationCases/marangoni-scale.c" \
   "${ROOT}/simulationCases/marangoni-multidrop.c" \
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
  "${QCC}" -source -D_MPI=1 marangoni-scale.c
  "${QCC}" -source -D_MPI=1 marangoni-multidrop.c
  mv _marangoni-scale.c _marangoni-scale-adaptive.c
  mv _marangoni-multidrop.c _marangoni-multidrop-adaptive.c
  "${QCC}" -source -D_MPI=1 -DUNIFORM=1 marangoni-scale.c
  mv _marangoni-scale.c _marangoni-scale-uniform.c
  "${QCC}" -source -D_MPI=1 -DUNIFORM=1 marangoni-multidrop.c
  mv _marangoni-multidrop.c _marangoni-multidrop-uniform.c
  mv _marangoni-scale-adaptive.c _marangoni-scale.c
  mv _marangoni-multidrop-adaptive.c _marangoni-multidrop.c
)

install -m 0644 "${WORKDIR}/_mpi-circle.c" "${ROOT}/generated/_mpi-circle.c"
install -m 0644 "${WORKDIR}/_mpi-laplacian.c" "${ROOT}/generated/_mpi-laplacian.c"
install -m 0644 "${WORKDIR}/_mpi-laplacian-2d.c" "${ROOT}/generated/_mpi-laplacian-2d.c"
install -m 0644 "${WORKDIR}/_marangoni-scale.c" "${ROOT}/generated/_marangoni-scale.c"
install -m 0644 "${WORKDIR}/_marangoni-multidrop.c" "${ROOT}/generated/_marangoni-multidrop.c"
install -m 0644 "${WORKDIR}/_marangoni-scale-uniform.c" \
  "${ROOT}/generated/_marangoni-scale-uniform.c"
install -m 0644 "${WORKDIR}/_marangoni-multidrop-uniform.c" \
  "${ROOT}/generated/_marangoni-multidrop-uniform.c"
echo "wrote ${ROOT}/generated/_mpi-circle.c"
echo "wrote ${ROOT}/generated/_mpi-laplacian.c"
echo "wrote ${ROOT}/generated/_mpi-laplacian-2d.c"
echo "wrote ${ROOT}/generated/_marangoni-scale.c"
echo "wrote ${ROOT}/generated/_marangoni-multidrop.c"
echo "wrote ${ROOT}/generated/_marangoni-scale-uniform.c"
echo "wrote ${ROOT}/generated/_marangoni-multidrop-uniform.c"
echo "qcc=${QCC}"
echo "BASILISK=${BASILISK}"
