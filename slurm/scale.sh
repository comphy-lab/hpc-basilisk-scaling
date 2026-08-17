#!/usr/bin/env bash
# Node-aligned scale-up for both stock tests.
# Default: gp_ehpc, 1-32 nodes. Pass QOS=gp_debug to use the one-job debug queue.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
CIRCLE_LEVEL="${CIRCLE_LEVEL:-14}"
LAPLACE_LEVEL="${LAPLACE_LEVEL:-9}"
NODES_LIST="${NODES_LIST:-1 2 4 8 16 32}"

submit() {
  local test="$1" nodes="$2" level="$3"
  local ntasks=$((nodes * 112))
  local extra=()
  # gp_debug allows one job per user; singleton is unnecessary on gp_ehpc.
  if [[ "${QOS}" == "gp_debug" ]]; then
    extra+=(--dependency=singleton --job-name=bsk-scale)
  else
    extra+=(--job-name="bsk-${test}-${ntasks}")
  fi
  sbatch --parsable \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --time=00:30:00 \
    --export=ALL,TEST="${test}",LEVEL="${level}" \
    "${extra[@]}" \
    "${SBATCH}"
}

echo "qos=${QOS} circle_level=${CIRCLE_LEVEL} laplacian_level=${LAPLACE_LEVEL}"
for nodes in ${NODES_LIST}; do
  echo "mpi-circle ${nodes} nodes -> $(submit mpi-circle "${nodes}" "${CIRCLE_LEVEL}")"
  echo "mpi-laplacian ${nodes} nodes -> $(submit mpi-laplacian "${nodes}" "${LAPLACE_LEVEL}")"
done
