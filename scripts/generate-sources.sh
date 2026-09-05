#!/usr/bin/env bash
# Emit portable C99 from the kernel tests and showcase solvers. Requires qcc.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
QCC="${QCC:-$(command -v qcc || true)}"
if [[ -z "${QCC}" ]]; then
  echo "generate-sources: qcc not found; set QCC or PATH" >&2
  exit 1
fi
export BASILISK="${BASILISK:-$(cd "$(dirname "${QCC}")" && pwd)}"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/basilisk-src.XXXXXX")"
cleanup() { rm -rf "${WORKDIR}"; }
trap cleanup EXIT

cp "${ROOT}/simulationCases/mpi-circle.c" \
   "${ROOT}/simulationCases/mpi-laplacian.c" \
   "${ROOT}/simulationCases/check_restriction.h" \
   "${ROOT}/simulationCases/marangoni-scale.c" \
   "${ROOT}/simulationCases/marangoni-multidrop.c" \
   "${ROOT}/simulationCases/marangoni-interact.c" \
   "${ROOT}/simulationCases/bursting-uniform.c" \
   "${ROOT}/simulationCases/taylorculick-uniform.c" \
   "${ROOT}/simulationCases/ve3d-impact-uniform.c" \
   "${ROOT}/simulationCases/drop-impact-uniform.c" \
   "${ROOT}/simulationCases/jumping-uniform-init.c" \
   "${ROOT}/simulationCases/jumping-uniform.c" \
   "${WORKDIR}/"
mkdir -p "${WORKDIR}/src-local"
cp "${ROOT}/simulationCases/activity-drop.c" "${WORKDIR}/"
cp "${ROOT}/src-local/"*.h "${WORKDIR}/src-local/"
# qcc resolves #include "eigen_decomposition.h" from the 3D log-conform header
# relative to the translation unit as well as src-local/.
cp "${ROOT}/src-local/eigen_decomposition.h" "${WORKDIR}/"

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
  "${QCC}" -source -D_MPI=1 marangoni-interact.c
  "${QCC}" -source -D_MPI=1 activity-drop.c
  mv _marangoni-scale-adaptive.c _marangoni-scale.c
  mv _marangoni-multidrop-adaptive.c _marangoni-multidrop.c

  "${QCC}" -source -disable-dimensions bursting-uniform.c
  mv _bursting-uniform.c _bursting-uniform-init.c
  "${QCC}" -source -D_MPI=1 -disable-dimensions bursting-uniform.c
  "${QCC}" -source -D_MPI=1 -disable-dimensions taylorculick-uniform.c
  "${QCC}" -grid=octree -source -D_MPI=1 -disable-dimensions ve3d-impact-uniform.c
  "${QCC}" -source -D_MPI=1 -disable-dimensions drop-impact-uniform.c
  "${QCC}" -grid=octree -source -disable-dimensions jumping-uniform-init.c
  "${QCC}" -grid=octree -source -D_MPI=1 -disable-dimensions jumping-uniform.c
)

install_gen() {
  local name="$1"
  python3 - "${WORKDIR}/${name}" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
# qcc -source on macOS bakes __APPLE__ into # if 1 and pulls fp_osx.h.
# Linux cluster compilers do not have that header; feenableexcept is in fenv.h.
# Darwin MAP_ANONYMOUS is 0x1000 (Linux MAP_EXECUTABLE); mmap then returns
# MAP_FAILED and init_grid segfaults. Restore the portable flag name.
text = text.replace('# include "fp_osx.h"\n', '')
text = text.replace('MAP_PRIVATE|0x1000', 'MAP_PRIVATE|MAP_ANONYMOUS')
path.write_text(text, encoding="utf-8")
PY
  install -m 0644 "${WORKDIR}/${name}" "${ROOT}/generated/${name}"
  echo "wrote ${ROOT}/generated/${name}"
}

install_gen _mpi-circle.c
install_gen _mpi-laplacian.c
install_gen _mpi-laplacian-2d.c
install_gen _marangoni-scale.c
install_gen _marangoni-multidrop.c
install_gen _marangoni-scale-uniform.c
install_gen _marangoni-multidrop-uniform.c
install_gen _marangoni-interact.c
install_gen _activity-drop.c
install_gen _bursting-uniform-init.c
install_gen _bursting-uniform.c
install_gen _taylorculick-uniform.c
install_gen _ve3d-impact-uniform.c
install_gen _drop-impact-uniform.c
install_gen _jumping-uniform-init.c
install_gen _jumping-uniform.c
echo "qcc=${QCC}"
echo "BASILISK=${BASILISK}"
