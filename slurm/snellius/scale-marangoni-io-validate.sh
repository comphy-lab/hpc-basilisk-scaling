#!/usr/bin/env bash
# One exclusive Snellius genoa node: packed adaptive Al Saud validation
# then uniform 64 pts/R dump+restart. Same physics as the MN5 job.
set -euo pipefail

PROJECT_DST="${PROJECT_DST:-/projects/0/your_project/hpc-basilisk-scaling}"
SBATCH="${PROJECT_DST}/slurm/snellius/run-marangoni-io-validate.sbatch"

sbatch --parsable "${SBATCH}"
