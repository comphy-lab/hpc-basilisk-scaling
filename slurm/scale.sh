#!/usr/bin/env bash
# Node-aligned gp_debug scale-up for both stock tests.
# Default: 1, 2, 4, 8, 16 nodes (112-1792 ranks).
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_debug}"
CIRCLE_LEVEL="${CIRCLE_LEVEL:-12}"
LAPLACE_LEVEL="${LAPLACE_LEVEL:-8}"
NODES_LIST="${NODES_LIST:-1 2 4 8 16}"

submit() {
  local test="$1" nodes="$2" level="$3"
  local ntasks=$((nodes * 112))
  sbatch --parsable \
    --job-name="scale-${test}-${ntasks}" \
    --qos="${QOS}" \
    --nodes="${nodes}" \
    --ntasks="${ntasks}" \
    --export=ALL,TEST="${test}",LEVEL="${level}" \
    "${SBATCH}"
}

echo "qos=${QOS} circle_level=${CIRCLE_LEVEL} laplacian_level=${LAPLACE_LEVEL}"
for nodes in ${NODES_LIST}; do
  echo "mpi-circle ${nodes} nodes -> $(submit mpi-circle "${nodes}" "${CIRCLE_LEVEL}")"
  echo "mpi-laplacian ${nodes} nodes -> $(submit mpi-laplacian "${nodes}" "${LAPLACE_LEVEL}")"
done
