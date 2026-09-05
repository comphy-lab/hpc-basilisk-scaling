#!/bin/bash
#SBATCH --job-name=bsk-unif
#SBATCH --partition=genoa
#SBATCH --ntasks=192
#SBATCH --cpus-per-task=1
#SBATCH --time=01:00:00
#SBATCH --exclusive

# Exclusive genoa allocation. --nodes/--ntasks come from the submit wrapper;
# RANKS is taken from the task table and srun uses that many ranks.
set -euo pipefail
ulimit -s unlimited

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env}"
PROJECT_DST="${PROJECT_DST:?set PROJECT_DST through site/*.env}"
TASK_FILE="${TASK_FILE:?set TASK_FILE to a slurm/snellius/*.tasks file}"
NITER="${NITER:-10}"

if [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
  echo "run-uniform-array.sbatch expects a Slurm job array" >&2
  exit 1
fi

mapfile -t TASKS < <(grep -vE '^[[:space:]]*(#|$)' "${TASK_FILE}")
if [[ "${SLURM_ARRAY_TASK_ID}" -ge "${#TASKS[@]}" ]]; then
  echo "array index ${SLURM_ARRAY_TASK_ID} >= ${#TASKS[@]}" >&2
  exit 1
fi

# shellcheck disable=SC2086
set -- ${TASKS[${SLURM_ARRAY_TASK_ID}]}
TEST="$1"
LEVEL="$2"
TASK_NITER="${3:-${NITER}}"
RANKS="$4"

BIN="${SCRATCH_DST}/bin/${TEST}"
OUTDIR="${SCRATCH_DST}/runs/${TEST}"
if [[ ! -x "${BIN}" ]]; then
  echo "missing binary ${BIN}" >&2
  exit 1
fi
mkdir -p "${OUTDIR}"
cd "${OUTDIR}"

TAG="${LEVEL}-${RANKS}"
echo "host=$(hostname) test=${TEST} level=${LEVEL} niter=${TASK_NITER} ranks=${RANKS} job=${SLURM_JOB_ID} array=${SLURM_ARRAY_TASK_ID}"
export OMP_NUM_THREADS=1

if [[ "${TEST}" == "bursting-uniform" || "${TEST}" == "jumping-uniform" ]]; then
  RESTART="${RESTART:-}"
  if [[ -z "${RESTART}" ]]; then
    if [[ -f "dumpInit-${LEVEL}" ]]; then
      RESTART="dumpInit-${LEVEL}"
    elif [[ -f dumpInit ]]; then
      RESTART="dumpInit"
    fi
  fi
  if [[ -z "${RESTART}" || ! -f "${RESTART}" ]]; then
    echo "missing restore file under ${OUTDIR} (tried dumpInit-${LEVEL}, dumpInit)" >&2
    exit 1
  fi
  srun -n "${RANKS}" "${BIN}" "${LEVEL}" "${TASK_NITER}" "${RESTART}" \
    > "out-${TAG}" 2> "log-${TAG}"
else
  srun -n "${RANKS}" "${BIN}" "${LEVEL}" "${TASK_NITER}" \
    > "out-${TAG}" 2> "log-${TAG}"
fi

echo "wrote ${OUTDIR}/out-${TAG}"
tail -n 20 "log-${TAG}" || true
grep '^#TIMING' "out-${TAG}" || true
