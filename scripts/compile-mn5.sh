#!/usr/bin/env bash
# Compile the generated C99 on a MareNostrum5 GPP login node. Do not run jobs here.
set -euo pipefail

SCRATCH_DST="${SCRATCH_DST:-/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling}"
CC="${CC:-mpicc}"

if [[ ! -f "${SCRATCH_DST}/generated/_mpi-circle.c" ]]; then
  echo "compile-mn5: missing generated sources under ${SCRATCH_DST}" >&2
  exit 1
fi

mkdir -p "${SCRATCH_DST}/bin"
cd "${SCRATCH_DST}/bin"

"${CC}" -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-circle.c" -o mpi-circle -lm
"${CC}" -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_mpi-laplacian.c" -o mpi-laplacian -lm

echo "compiled ${SCRATCH_DST}/bin/mpi-circle"
echo "compiled ${SCRATCH_DST}/bin/mpi-laplacian"
ls -l "${SCRATCH_DST}/bin/mpi-circle" "${SCRATCH_DST}/bin/mpi-laplacian"
