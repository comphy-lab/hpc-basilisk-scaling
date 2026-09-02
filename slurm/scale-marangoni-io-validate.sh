#!/usr/bin/env bash
# One exclusive MareNostrum5 GPP node: uniform 64 pts/R dump+restart,
# then adaptive Al Saud validation (levels 7-12, t/t0=3, dumps on).
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run-marangoni-io-validate.sbatch"
QOS="${QOS:-gp_ehpc}"

sbatch --parsable "${SITE_SBATCH_ARGS[@]}" --export=ALL --qos="${QOS}" "${SBATCH}"
