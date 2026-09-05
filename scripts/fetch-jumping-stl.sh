#!/usr/bin/env bash
# Download the Jumping-Drops binary STL from Git LFS. The object is ~282 MiB
# and is gitignored; stage it to the cluster, do not commit it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OID="f4754ec23c0c0d058d51e21737b32300bc5fc555456e99ec916d8fcf25f3190d"
SIZE="282207584"
DEST="${1:-${ROOT}/simulationCases/data/InitialCondition.stl}"

mkdir -p "$(dirname "${DEST}")"
if [[ -f "${DEST}" ]]; then
  actual="$(wc -c < "${DEST}" | tr -d ' ')"
  if [[ "${actual}" == "${SIZE}" ]]; then
    echo "already present ${DEST} (${actual} bytes)"
    exit 0
  fi
fi

batch="$(mktemp)"
trap 'rm -f "${batch}"' EXIT
curl -fsS -X POST \
  -H "Accept: application/vnd.git-lfs+json" \
  -H "Content-Type: application/vnd.git-lfs+json" \
  https://github.com/comphy-lab/Jumping-Drops.git/info/lfs/objects/batch \
  -d "{\"operation\":\"download\",\"transfers\":[\"basic\"],\"objects\":[{\"oid\":\"${OID}\",\"size\":${SIZE}}]}" \
  > "${batch}"

href="$(python3 - "${batch}" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1], encoding="utf-8"))
objs = payload.get("objects") or []
if len(objs) != 1:
    raise SystemExit("unexpected LFS batch response")
actions = (objs[0].get("actions") or {}).get("download") or {}
href = actions.get("href")
if not href:
    raise SystemExit("LFS batch response has no download href")
print(href)
PY
)"

curl -fL --retry 3 -o "${DEST}.partial" "${href}"
actual="$(wc -c < "${DEST}.partial" | tr -d ' ')"
if [[ "${actual}" != "${SIZE}" ]]; then
  echo "fetch-jumping-stl: size ${actual} != ${SIZE}" >&2
  exit 1
fi
mv "${DEST}.partial" "${DEST}"
echo "wrote ${DEST} (${actual} bytes)"
