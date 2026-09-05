#!/bin/bash
#SBATCH --job-name=bsk-unif-init
#SBATCH --partition=genoa
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=192
#SBATCH --time=01:00:00
#SBATCH --exclusive

# Serial dumpInit for bursting and/or jumping-drops.
set -euo pipefail
ulimit -s unlimited

module purge
module load 2024
module load OpenMPI/5.0.3-GCC-13.3.0

SCRATCH_DST="${SCRATCH_DST:?set SCRATCH_DST through site/*.env}"
PROJECT_DST="${PROJECT_DST:?set PROJECT_DST through site/*.env}"
LEVEL_BURST="${LEVEL_BURST:-10}"
LEVELS_BURST="${LEVELS_BURST:-${LEVEL_BURST}}"
LEVEL_JUMP="${LEVEL_JUMP:-7}"
SKIP_BURST="${SKIP_BURST:-0}"
SKIP_JUMP="${SKIP_JUMP:-0}"

burst_bin="${SCRATCH_DST}/bin/bursting-uniform-init"
jump_bin="${SCRATCH_DST}/bin/jumping-uniform-init"
if [[ "${SKIP_BURST}" != "1" && ! -x "${burst_bin}" ]]; then
  echo "missing ${burst_bin}" >&2
  exit 1
fi
if [[ "${SKIP_JUMP}" != "1" && ! -x "${jump_bin}" ]]; then
  echo "missing ${jump_bin}" >&2
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

if [[ "${SKIP_JUMP}" == "1" ]]; then
  echo "skipped jumping-uniform-init"
  exit 0
fi

jump_out="${SCRATCH_DST}/runs/jumping-uniform"
stl="${PROJECT_DST}/simulationCases/data/InitialCondition.stl"
if [[ ! -f "${stl}" ]]; then
  echo "missing ${stl}; run scripts/fetch-jumping-stl.sh before staging" >&2
  exit 1
fi
mkdir -p "${jump_out}"
cp -f "${stl}" "${jump_out}/InitialCondition.stl"
cd "${jump_out}"
echo "host=$(hostname) jumping-uniform-init LEVEL=${LEVEL_JUMP} job=${SLURM_JOB_ID}"
"${jump_bin}" "${LEVEL_JUMP}" \
  > "init-out-${LEVEL_JUMP}" 2> "init-log-${LEVEL_JUMP}"
test -f dumpInit
echo "wrote ${jump_out}/dumpInit"
