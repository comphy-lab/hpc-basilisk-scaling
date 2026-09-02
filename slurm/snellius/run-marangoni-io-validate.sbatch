#!/bin/bash
#SBATCH --job-name=snl-io-val
#SBATCH --partition=genoa
#SBATCH --nodes=1
#SBATCH --ntasks=192
#SBATCH --cpus-per-task=1
#SBATCH --time=12:00:00
#SBATCH --exclusive

# One genoa node: 192 cores = sum of (ranks * 4 cpt) over L7--L12, then
# a 64-rank uniform L10 dump+restart. Rank counts keep roughly
# 500--2000 adapted cells per rank:
#   L7   8 pts/R   2 ranks * 4 cpt =   8 cores
#   L8  16 pts/R   2 ranks * 4 cpt =   8 cores
#   L9  32 pts/R   4 ranks * 4 cpt =  16 cores
#   L10 64 pts/R   8 ranks * 4 cpt =  32 cores
#   L11 128 pts/R 16 ranks * 4 cpt =  64 cores
#   L12 256 pts/R 16 ranks * 4 cpt =  64 cores
# Sum = 192.

set -euo pipefail

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env (scripts/site-env.sh)}"
BIN_UNI="${SCRATCH_DST}/bin/marangoni-scale-uniform"
BIN_AD="${SCRATCH_DST}/bin/marangoni-scale"
IO_DIR="${SCRATCH_DST}/runs/marangoni-io/L10-n64"
VAL_ROOT="${SCRATCH_DST}/runs/marangoni-validate"
CPT=4

if [[ ! -x "${BIN_UNI}" || ! -x "${BIN_AD}" ]]; then
  echo "missing binaries ${BIN_UNI} ${BIN_AD}" >&2
  exit 1
fi

export OMP_NUM_THREADS=1
echo "host=$(hostname) job=${SLURM_JOB_ID} start=$(date -u +%Y-%m-%dT%H:%MZ)"

run_level() {
  local level="$1" ranks="$2"
  local case="${VAL_ROOT}/L${level}"
  mkdir -p "${case}"
  rm -f "${case}/out" "${case}/log" "${case}/restart" "${case}"/snapshot-*
  echo "validate LEVEL=${level} pts/R=$((1 << (level - 4))) n=${ranks} cpt=${CPT} TMAX/t0=3 dump/t0=0.1"
  (
    cd "${case}"
    srun --overlap --exact --ntasks="${ranks}" --cpus-per-task="${CPT}" \
      --cpu-bind=cores \
      "${BIN_AD}" "${level}" 3 0.1 \
      > out 2> log
  )
  echo "validate LEVEL=${level} done $(date -u +%Y-%m-%dT%H:%MZ)"
}

pids=()
run_level 7 2 & pids+=("$!")
run_level 8 2 & pids+=("$!")
run_level 9 4 & pids+=("$!")
run_level 10 8 & pids+=("$!")
run_level 11 16 & pids+=("$!")
run_level 12 16 & pids+=("$!")

status=0
for pid in "${pids[@]}"; do
  if ! wait "${pid}"; then
    echo "a validation case failed pid=${pid}" >&2
    status=1
  fi
done
if [[ "${status}" -ne 0 ]]; then
  echo "validation pack had a failure; still running I/O" >&2
fi

mkdir -p "${IO_DIR}"
cd "${IO_DIR}"
rm -f out-cold log-cold out-restart log-restart restart snapshot-*
echo "I/O cold start uniform L10 n=64 TMAX/t0=0.05 dump/t0=0.025"
srun --exact --ntasks=64 --cpus-per-task=1 --cpu-bind=cores \
  "${BIN_UNI}" 10 0.05 0.025 \
  > out-cold 2> log-cold
echo "I/O restart from ${IO_DIR}/restart to TMAX/t0=0.10"
srun --exact --ntasks=64 --cpus-per-task=1 --cpu-bind=cores \
  "${BIN_UNI}" 10 0.10 0.025 restart \
  > out-restart 2> log-restart
ls -l restart snapshot-* 2>/dev/null || true
echo "I/O done $(date -u +%Y-%m-%dT%H:%MZ)"

echo "all done $(date -u +%Y-%m-%dT%H:%MZ) validation_status=${status}"
for LEVEL in 7 8 9 10 11 12; do
  tail -n 3 "${VAL_ROOT}/L${LEVEL}/out" || true
done
tail -n 5 "${IO_DIR}/out-cold" "${IO_DIR}/out-restart" || true
exit "${status}"
