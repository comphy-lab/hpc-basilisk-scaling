#!/bin/bash
#SBATCH --job-name=bsk-kernel
#SBATCH --account=your_account
#SBATCH --qos=gp_ehpc
#SBATCH --ntasks=2
#SBATCH --cpus-per-task=1
#SBATCH --time=00:20:00
#SBATCH --output=/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling/runs/%x-%j.out
#SBATCH --error=/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling/runs/%x-%j.err
#SBATCH --exclusive

set -euo pipefail

TEST="${TEST:-mpi-circle}"
LEVEL="${LEVEL:-8}"
MINLEVEL="${MINLEVEL:-5}"
SCRATCH_DST="${SCRATCH_DST:-/gpfs/scratch/your_account/your_user/mn5-basilisk-scaling}"
BIN="${SCRATCH_DST}/bin/${TEST}"
OUTDIR="${SCRATCH_DST}/runs/${TEST}"

if [[ ! -x "${BIN}" ]]; then
  echo "missing binary ${BIN}" >&2
  exit 1
fi

mkdir -p "${OUTDIR}"
cd "${OUTDIR}"

NTASKS="${SLURM_NTASKS}"
TAG="${LEVEL}-${NTASKS}"
echo "host=$(hostname) test=${TEST} level=${LEVEL} ntasks=${NTASKS} job=${SLURM_JOB_ID}"

export OMP_NUM_THREADS=1
if [[ "${TEST}" == "mpi-circle" ]]; then
  srun --mpi=pmi2 -n "${NTASKS}" "${BIN}" "${LEVEL}" "${MINLEVEL}" \
    > "out-${TAG}" 2> "log-${TAG}"
else
  srun --mpi=pmi2 -n "${NTASKS}" "${BIN}" "${LEVEL}" \
    > "out-${TAG}" 2> "log-${TAG}"
fi

echo "wrote ${OUTDIR}/out-${TAG}"
tail -n 20 "log-${TAG}" || true
