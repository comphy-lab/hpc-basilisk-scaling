#!/usr/bin/env bash
# Load one cluster's account and path settings. Source this file, then call
#   site_env mn5        or        site_env snellius
# It reads site/<name>.env from the repository root (copy the matching
# .env.example and fill it in; the .env files are ignored by Git), then
# checks that every variable the wrappers need is set. Pass
# "${SITE_SBATCH_ARGS[@]}" to sbatch so the account and log paths follow
# the site file instead of living in the batch scripts.

site_env() {
  local name="${1:?site_env: expected mn5 or snellius}"
  case "${name}" in
    mn5|snellius) ;;
    *)
      echo "site-env: unsupported site '${name}' (expected mn5 or snellius)" >&2
      return 2
      ;;
  esac
  local root
  root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  local file="${SITE_ENV_FILE:-${root}/site/${name}.env}"
  if [[ -f "${file}" ]]; then
    # shellcheck disable=SC1090
    source "${file}"
  fi

  local missing=()
  local var
  for var in PROJECT_DST SCRATCH_DST SLURM_ACCOUNT; do
    if [[ -z "${!var:-}" ]]; then
      missing+=("${var}")
    fi
  done
  if [[ "${#missing[@]}" -gt 0 ]]; then
    echo "site-env: ${missing[*]} not set; copy site/${name}.env.example to ${file} and fill it in" >&2
    return 1
  fi
  export PROJECT_DST SCRATCH_DST SLURM_ACCOUNT

  # shellcheck disable=SC2034  # consumed by the sourcing wrapper
  SITE_SBATCH_ARGS=(
    --account="${SLURM_ACCOUNT}"
    --output="${SCRATCH_DST}/runs/%x-%j.out"
    --error="${SCRATCH_DST}/runs/%x-%j.err"
  )
}
