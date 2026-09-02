#!/bin/bash
#SBATCH --job-name=bsk-kernel
#SBATCH --partition=genoa
#SBATCH --ntasks=192
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --exclusive

set -euo pipefail

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

TEST="${TEST:-mpi-circle}"
LEVEL="${LEVEL:-8}"
MINLEVEL="${MINLEVEL:-5}"
TMAX="${TMAX:-0.5}"
NDROPS="${NDROPS:-2}"
SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env (scripts/site-env.sh)}"
BIN="${SCRATCH_DST}/bin/${TEST}"
OUTDIR="${SCRATCH_DST}/runs/${TEST}"

if [[ ! -x "${BIN}" ]]; then
  echo "missing binary ${BIN}" >&2
  exit 1
fi

mkdir -p "${OUTDIR}"
cd "${OUTDIR}"

NTASKS="${SLURM_NTASKS}"
if [[ -n "${RANKS:-}" && "${RANKS}" != "${NTASKS}" ]]; then
  echo "RANKS=${RANKS} does not match SLURM_NTASKS=${NTASKS}" >&2
  exit 1
fi
if [[ "${TEST}" == marangoni-multidrop* ]]; then
  TAG="${NDROPS}-${NTASKS}"
else
  TAG="${LEVEL}-${NTASKS}"
fi
TAG="${TAG_OVERRIDE:-${TAG}}"
echo "host=$(hostname) test=${TEST} level=${LEVEL} ndrops=${NDROPS} ntasks=${NTASKS} job=${SLURM_JOB_ID}"

export OMP_NUM_THREADS=1
if [[ "${TEST}" == "mpi-circle" ]]; then
  srun -n "${NTASKS}" "${BIN}" "${LEVEL}" "${MINLEVEL}" \
    > "out-${TAG}" 2> "log-${TAG}"
elif [[ "${TEST}" == marangoni-scale* ]]; then
  srun -n "${NTASKS}" "${BIN}" "${LEVEL}" "${TMAX}" \
    > "out-${TAG}" 2> "log-${TAG}"
elif [[ "${TEST}" == marangoni-multidrop* ]]; then
  srun -n "${NTASKS}" "${BIN}" "${NDROPS}" "${TMAX}" \
    > "out-${TAG}" 2> "log-${TAG}"
else
  srun -n "${NTASKS}" "${BIN}" "${LEVEL}" \
    > "out-${TAG}" 2> "log-${TAG}"
fi

echo "wrote ${OUTDIR}/out-${TAG}"
tail -n 20 "log-${TAG}" || true
