#!/bin/bash
#SBATCH --job-name=bsk-io-val
#SBATCH --qos=gp_ehpc
#SBATCH --nodes=1
#SBATCH --ntasks=112
#SBATCH --cpus-per-task=1
#SBATCH --time=12:00:00
#SBATCH --exclusive

set -euo pipefail

SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env (scripts/site-env.sh)}"
BIN_UNI="${SCRATCH_DST}/bin/marangoni-scale-uniform"
BIN_AD="${SCRATCH_DST}/bin/marangoni-scale"
IO_DIR="${SCRATCH_DST}/runs/marangoni-io/L10-n64"
VAL_ROOT="${SCRATCH_DST}/runs/marangoni-validate"

if [[ ! -x "${BIN_UNI}" || ! -x "${BIN_AD}" ]]; then
  echo "missing binaries ${BIN_UNI} ${BIN_AD}" >&2
  exit 1
fi

export OMP_NUM_THREADS=1
echo "host=$(hostname) job=${SLURM_JOB_ID} start=$(date -u +%Y-%m-%dT%H:%MZ)"

# Adaptive Al Saud window first so a later I/O restart failure cannot
# skip v(t). Sequential, 16 ranks (axi adaptive knee), t/t0=3.
for LEVEL in 7 8 9 10 11 12; do
  CASE="${VAL_ROOT}/L${LEVEL}"
  mkdir -p "${CASE}"
  echo "validate LEVEL=${LEVEL} pts/R=$((1 << (LEVEL - 4))) n=16 TMAX/t0=3 dump/t0=0.1"
  (
    cd "${CASE}"
    srun --mpi=pmi2 -n 16 "${BIN_AD}" "${LEVEL}" 3 0.1 \
      > out 2> log
  )
  echo "validate LEVEL=${LEVEL} done $(date -u +%Y-%m-%dT%H:%MZ)"
done

mkdir -p "${IO_DIR}"
cd "${IO_DIR}"
echo "I/O cold start uniform L10 n=64 TMAX/t0=0.05 dump/t0=0.025"
srun --mpi=pmi2 -n 64 "${BIN_UNI}" 10 0.05 0.025 \
  > out-cold 2> log-cold
echo "I/O restart from ${IO_DIR}/restart to TMAX/t0=0.10"
srun --mpi=pmi2 -n 64 "${BIN_UNI}" 10 0.10 0.025 restart \
  > out-restart 2> log-restart
ls -l restart snapshot-* 2>/dev/null || true
echo "I/O done $(date -u +%Y-%m-%dT%H:%MZ)"

echo "all done $(date -u +%Y-%m-%dT%H:%MZ)"
tail -n 5 "${IO_DIR}/out-cold" "${IO_DIR}/out-restart" || true
for LEVEL in 7 8 9 10 11 12; do
  tail -n 3 "${VAL_ROOT}/L${LEVEL}/out" || true
done
