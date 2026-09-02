#!/usr/bin/env bash
# One exclusive MN5 GPP node: 8 drops in a radial sigma well, video dumps.
# 16 MPI ranks (do not overdecompose the adaptive interface). Exclusive
# node still charges 112 cores.
set -euo pipefail

# shellcheck source=scripts/site-env.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/scripts/site-env.sh"
site_env mn5
SBATCH="${PROJECT_DST}/slurm/run.sbatch"
QOS="${QOS:-gp_ehpc}"
NDROPS="${NDROPS:-8}"
TMAX="${TMAX:-12}"
DUMP_EVERY="${DUMP_EVERY:-0.1}"
RANKS="${RANKS:-16}"
WALL="${WALL:-12:00:00}"

sbatch --parsable \
  "${SITE_SBATCH_ARGS[@]}" \
  --job-name="bsk-interact-${NDROPS}d" \
  --qos="${QOS}" \
  --nodes=1 \
  --ntasks=112 \
  --exclusive \
  --time="${WALL}" \
  --export=ALL,TEST=marangoni-interact,NDROPS="${NDROPS}",RANKS="${RANKS}",TMAX="${TMAX}",DUMP_EVERY="${DUMP_EVERY}",TAG_OVERRIDE="interact-${NDROPS}d" \
  "${SBATCH}"
