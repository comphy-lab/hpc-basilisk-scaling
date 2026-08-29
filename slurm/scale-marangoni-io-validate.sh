#!/usr/bin/env bash
# One exclusive MareNostrum5 GPP node: uniform 64 pts/R dump+restart,
# then adaptive Al Saud validation (levels 7-12, t/t0=3, dumps on).
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/gpfs/projects/your_account/mn5-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/run-marangoni-io-validate.sbatch"
QOS="${QOS:-gp_ehpc}"

sbatch --parsable --qos="${QOS}" "${SBATCH}"
