#!/usr/bin/env bash
# One exclusive Snellius genoa node: packed adaptive Al Saud validation
# then uniform 64 pts/R dump+restart. Same physics as the MN5 job.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/scripts/site-env.sh"
site_env snellius
SBATCH="${PROJECT_DST}/slurm/snellius/run-marangoni-io-validate.sbatch"

sbatch --parsable "${SITE_SBATCH_ARGS[@]}" --export=ALL "${SBATCH}"
