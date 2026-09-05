#!/usr/bin/env bash
# Compile the generated C99 on a Snellius login node. Do not run jobs here.
# Reads site/snellius.env.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/site-env.sh"
site_env snellius

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

need=(
  _mpi-circle.c
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
  if [[ ! -f "${SCRATCH_DST}/generated/${f}" ]]; then
    echo "compile-snellius: missing ${SCRATCH_DST}/generated/${f}" >&2
    exit 1
  fi
done

COMPILE_SET="${COMPILE_SET:-all}"

mkdir -p "${SCRATCH_DST}/bin"
cd "${SCRATCH_DST}/bin"

if [[ "${COMPILE_SET}" == "all" ]]; then
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-circle.c" -o mpi-circle -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-laplacian.c" -o mpi-laplacian -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-laplacian-2d.c" -o mpi-laplacian-2d -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-scale.c" -o marangoni-scale -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-multidrop.c" -o marangoni-multidrop -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-scale-uniform.c" -o marangoni-scale-uniform -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-multidrop-uniform.c" \
  -o marangoni-multidrop-uniform -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-interact.c" -o marangoni-interact -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_activity-drop.c" -o activity-drop -lm
fi

# axi/two-phase C99 from macOS qcc enables signaling-NaN FPE when compiled
# without OpenMP. MN5 already uses these flags for the same class of solvers.
TWOPHASE_CFLAGS="-Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans -D_GNU_SOURCE=1"
gcc ${TWOPHASE_CFLAGS} -fopenmp \
  "${SCRATCH_DST}/generated/_bursting-uniform-init.c" -o bursting-uniform-init -lm
mpicc ${TWOPHASE_CFLAGS} -D_MPI=1 \
  "${SCRATCH_DST}/generated/_bursting-uniform.c" -o bursting-uniform -lm
mpicc ${TWOPHASE_CFLAGS} -D_MPI=1 \
  "${SCRATCH_DST}/generated/_taylorculick-uniform.c" -o taylorculick-uniform -lm
mpicc ${TWOPHASE_CFLAGS} -D_MPI=1 \
  "${SCRATCH_DST}/generated/_ve3d-impact-uniform.c" -o ve3d-impact-uniform -lm
mpicc ${TWOPHASE_CFLAGS} -D_MPI=1 \
  "${SCRATCH_DST}/generated/_drop-impact-uniform.c" -o drop-impact-uniform -lm
gcc ${TWOPHASE_CFLAGS} -fopenmp \
  "${SCRATCH_DST}/generated/_jumping-uniform-init.c" -o jumping-uniform-init -lm
mpicc ${TWOPHASE_CFLAGS} -D_MPI=1 \
  "${SCRATCH_DST}/generated/_jumping-uniform.c" -o jumping-uniform -lm

echo "compiled binaries under ${SCRATCH_DST}/bin"
ls -l bursting-uniform-init bursting-uniform taylorculick-uniform \
  ve3d-impact-uniform drop-impact-uniform jumping-uniform-init jumping-uniform
if [[ "${COMPILE_SET}" == "all" ]]; then
  ls -l mpi-circle mpi-laplacian mpi-laplacian-2d marangoni-scale \
    marangoni-multidrop marangoni-scale-uniform marangoni-multidrop-uniform \
    marangoni-interact activity-drop
fi
