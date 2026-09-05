#!/usr/bin/env bash
# Serial dumpInit for bursting and jumping-drops, then the MPI rank sweeps.
# Geometric-init cases (2-4) can be submitted immediately; restore cases
# (1, 5) take an optional init job id for --dependency=afterok. Omit it
# when dumpInit is already on scratch.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PARTITION="${PARTITION:-genoa}"
TIME="${TIME:-01:00:00}"
ARRAY_SBATCH="${PROJECT_DST}/slurm/snellius/run-uniform-array.sbatch"
INIT_SBATCH="${PROJECT_DST}/slurm/snellius/run-uniform-init.sbatch"
MPI_TASKS="${PROJECT_DST}/slurm/snellius/uniform-mpi.tasks"
RESTORE_TASKS="${PROJECT_DST}/slurm/snellius/uniform-restore.tasks"

MODE="${1:-all}"

submit_init() {
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="snl-unif-init" \
    --partition="${PARTITION}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task=192 \
    --exclusive \
    --time="${TIME}" \
    --export=ALL,SKIP_BURST="${SKIP_BURST:-0}",SKIP_JUMP="${SKIP_JUMP:-0}",LEVEL_JUMP="${LEVEL_JUMP:-7}",LEVELS_BURST="${LEVELS_BURST:-10}" \
    "${INIT_SBATCH}"
}

submit_array() {
  local name="$1" tasks="$2" dep="${3:-}"
  submit_array_nodes "${name}" "${tasks}" 1 "${dep}" 6
}

submit_array_nodes() {
  local name="$1" tasks="$2" nodes="$3" dep="${4:-}" throttle="${5:-6}"
  local ntasks slurm_ntasks
  ntasks="$(grep -vE '^[[:space:]]*(#|$)' "${tasks}" | wc -l | tr -d ' ')"
  slurm_ntasks=$((nodes * 192))
  local extra=()
  if [[ -n "${dep}" ]]; then
    extra+=(--dependency="afterok:${dep}")
  fi
  sbatch --parsable \
    "${SITE_SBATCH_ARGS[@]}" \
    --job-name="${name}" \
    --partition="${PARTITION}" \
    --nodes="${nodes}" \
    --ntasks="${slurm_ntasks}" \
    --cpus-per-task=1 \
    --exclusive \
    --time="${TIME}" \
    --array="0-$((ntasks - 1))%${throttle}" \
    --export=ALL,TASK_FILE="${tasks}",NITER=10 \
    "${extra[@]}" \
    "${ARRAY_SBATCH}"
}

case "${MODE}" in
  init)
    echo "init -> $(submit_init)"
    ;;
  init-jump)
    SKIP_BURST=1
    echo "init -> $(submit_init)"
    ;;
  mpi)
    echo "mpi-array -> $(submit_array snl-unif-mpi "${MPI_TASKS}")"
    ;;
  restore)
    dep="${2:-}"
    echo "restore-array -> $(submit_array snl-unif-rst "${RESTORE_TASKS}" "${dep}")"
    ;;
  all)
    init_id="$(submit_init)"
    mpi_id="$(submit_array snl-unif-mpi "${MPI_TASKS}")"
    rst_id="$(submit_array snl-unif-rst "${RESTORE_TASKS}" "${init_id}")"
    echo "init=${init_id}"
    echo "mpi-array=${mpi_id}"
    echo "restore-array=${rst_id}"
    ;;
  fig567)
    FIG567_N1="${PROJECT_DST}/slurm/snellius/uniform-fig567-n1.tasks"
    FIG567_N2="${PROJECT_DST}/slurm/snellius/uniform-fig567-n2.tasks"
    FIG567_N4="${PROJECT_DST}/slurm/snellius/uniform-fig567-n4.tasks"
    SKIP_JUMP=1
    LEVELS_BURST="9 11"
    init_id="$(submit_init)"
    n1_id="$(submit_array_nodes snl-f567-n1 "${FIG567_N1}" 1 "${init_id}" 6)"
    n2_id="$(submit_array_nodes snl-f567-n2 "${FIG567_N2}" 2 "${init_id}" 3)"
    n4_id="$(submit_array_nodes snl-f567-n4 "${FIG567_N4}" 4 "${init_id}" 2)"
    echo "init=${init_id}"
    echo "n1-array=${n1_id}"
    echo "n2-array=${n2_id}"
    echo "n4-array=${n4_id}"
    ;;
  *)
    echo "usage: $0 [all|init|init-jump|mpi|restore [INIT_JOBID]|fig567]" >&2
    exit 2
    ;;
esac
