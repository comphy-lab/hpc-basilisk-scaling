#!/usr/bin/env bash
# Compile the generated C99 on a Snellius login node. Do not run jobs here.
set -euo pipefail

SCRATCH_DST="${SCRATCH_DST:-/scratch-shared/your_user/hpc-basilisk-scaling}"

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

if [[ ! -f "${SCRATCH_DST}/generated/_mpi-circle.c" ]]; then
  echo "compile-snellius: missing generated sources under ${SCRATCH_DST}" >&2
  exit 1
fi

mkdir -p "${SCRATCH_DST}/bin"
cd "${SCRATCH_DST}/bin"

mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-circle.c" -o mpi-circle -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-laplacian.c" -o mpi-laplacian -lm
mpicc -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-laplacian-2d.c" -o mpi-laplacian-2d -lm

echo "compiled ${SCRATCH_DST}/bin/mpi-circle"
echo "compiled ${SCRATCH_DST}/bin/mpi-laplacian"
echo "compiled ${SCRATCH_DST}/bin/mpi-laplacian-2d"
ls -l "${SCRATCH_DST}/bin/mpi-circle" "${SCRATCH_DST}/bin/mpi-laplacian" \
  "${SCRATCH_DST}/bin/mpi-laplacian-2d"
