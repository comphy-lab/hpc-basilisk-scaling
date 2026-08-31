#!/usr/bin/env bash
# Compile the generated C99 on a MareNostrum5 GPP login node. Do not run jobs here.
set -euo pipefail

SCRATCH_DST="${SCRATCH_DST:-/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling}"
CC="${CC:-mpicc}"

if [[ ! -f "${SCRATCH_DST}/generated/_mpi-circle.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-scale.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-multidrop.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-scale-uniform.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-multidrop-uniform.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-interact.c" || ! -f "${SCRATCH_DST}/generated/_activity-drop.c" ]]; then
  echo "compile-mn5: missing generated sources under ${SCRATCH_DST}" >&2
  exit 1
fi

mkdir -p "${SCRATCH_DST}/bin"
cd "${SCRATCH_DST}/bin"

# Intel mpicc needs an explicit -lmpi after the object on this module stack.
# -diag-disable=10441 silences the Intel Classic deprecation remark.
"${CC}" -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 -diag-disable=10441 \
  "${SCRATCH_DST}/generated/_mpi-circle.c" -o mpi-circle -lm -lmpi
"${CC}" -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 -diag-disable=10441 \
  "${SCRATCH_DST}/generated/_mpi-laplacian.c" -o mpi-laplacian -lm -lmpi
"${CC}" -Wall -std=c99 -O2 -D_MPI=1 -D_GNU_SOURCE=1 -diag-disable=10441 \
  "${SCRATCH_DST}/generated/_mpi-laplacian-2d.c" -o mpi-laplacian-2d -lm -lmpi
# Intel icc -O2 traps a SIGFPE in the axi+CLSVOF+integral first step.
# Intel MPI + GCC frontend matches the Snellius numerics and still
# launches with srun --mpi=pmi2.
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-scale.c" -o marangoni-scale -lm -lmpi
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-multidrop.c" -o marangoni-multidrop -lm -lmpi
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-scale-uniform.c" -o marangoni-scale-uniform -lm -lmpi
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-multidrop-uniform.c" \
  -o marangoni-multidrop-uniform -lm -lmpi
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_marangoni-interact.c" \
  -o marangoni-interact -lm -lmpi
I_MPI_CC=gcc "${CC}" -Wall -std=c99 -O2 -fno-trapping-math -fno-signaling-nans \
  -D_MPI=1 -D_GNU_SOURCE=1 \
  "${SCRATCH_DST}/generated/_activity-drop.c" \
  -o activity-drop -lm -lmpi

echo "compiled ${SCRATCH_DST}/bin/mpi-circle"
echo "compiled ${SCRATCH_DST}/bin/mpi-laplacian"
echo "compiled ${SCRATCH_DST}/bin/mpi-laplacian-2d"
echo "compiled ${SCRATCH_DST}/bin/marangoni-scale"
echo "compiled ${SCRATCH_DST}/bin/marangoni-multidrop"
echo "compiled ${SCRATCH_DST}/bin/marangoni-scale-uniform"
echo "compiled ${SCRATCH_DST}/bin/marangoni-multidrop-uniform"
echo "compiled ${SCRATCH_DST}/bin/marangoni-interact"
echo "compiled ${SCRATCH_DST}/bin/activity-drop"
ls -l "${SCRATCH_DST}/bin/mpi-circle" "${SCRATCH_DST}/bin/mpi-laplacian" \
  "${SCRATCH_DST}/bin/mpi-laplacian-2d" "${SCRATCH_DST}/bin/marangoni-scale" \
  "${SCRATCH_DST}/bin/marangoni-multidrop" \
  "${SCRATCH_DST}/bin/marangoni-scale-uniform" \
  "${SCRATCH_DST}/bin/marangoni-multidrop-uniform" \
  "${SCRATCH_DST}/bin/marangoni-interact" \
  "${SCRATCH_DST}/bin/activity-drop"
