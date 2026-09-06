#!/bin/bash
#SBATCH --job-name=bsk-unif-init
#SBATCH --partition=genoa
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=192
#SBATCH --time=01:00:00
#SBATCH --exclusive

# Serial dumpInit for bursting.
set -euo pipefail
ulimit -s unlimited

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env}"
PROJECT_DST="${PROJECT_DST:?set PROJECT_DST through site/*.env}"
LEVEL_BURST="${LEVEL_BURST:-10}"
LEVELS_BURST="${LEVELS_BURST:-${LEVEL_BURST}}"
SKIP_BURST="${SKIP_BURST:-0}"

burst_bin="${SCRATCH_DST}/bin/bursting-uniform-init"
if [[ "${SKIP_BURST}" != "1" && ! -x "${burst_bin}" ]]; then
  echo "missing ${burst_bin}" >&2
  exit 1
fi

burst_out="${SCRATCH_DST}/runs/bursting-uniform"
if [[ "${SKIP_BURST}" != "1" ]]; then
  mkdir -p "${burst_out}/DataFiles"
  cp -f "${PROJECT_DST}/simulationCases/DataFiles/Bo0.0010.dat" \
    "${burst_out}/DataFiles/"
  cd "${burst_out}"
  export OMP_NUM_THREADS=1
  if [[ -f dumpInit && ! -f dumpInit-10 ]]; then
    cp -f dumpInit dumpInit-10
  fi
  for level in ${LEVELS_BURST}; do
    echo "host=$(hostname) bursting-uniform-init LEVEL=${level} job=${SLURM_JOB_ID}"
    "${burst_bin}" "${level}" \
      > "init-out-${level}" 2> "init-log-${level}"
    test -f dumpInit
    mv -f dumpInit "dumpInit-${level}"
    echo "wrote ${burst_out}/dumpInit-${level}"
  done
else
  echo "skipped bursting-uniform-init"
fi
