#!/usr/bin/env bash
# Compile the generated C99 on a Snellius login node. Do not run jobs here.
set -euo pipefail

SCRATCH_DST="${SCRATCH_DST:-/scratch-shared/your_user/hpc-basilisk-scaling}"

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

if [[ ! -f "${SCRATCH_DST}/generated/_mpi-circle.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-scale.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-multidrop.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-scale-uniform.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-multidrop-uniform.c" || ! -f "${SCRATCH_DST}/generated/_marangoni-interact.c" || ! -f "${SCRATCH_DST}/generated/_activity-drop.c" ]]; then
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
