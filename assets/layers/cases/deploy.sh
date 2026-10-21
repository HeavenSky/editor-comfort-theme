#!/usr/bin/env bash
set -euo pipefail
export AWS_PROFILE=dev
ROOT="$(cd "$(dirname "$0")" && pwd)"
for f in "$ROOT"/configs/*.yaml; do
  if [[ -f "$f" && "$f" != *test* ]]; then
    echo "deploy $f" >&2
    kubectl apply -f "$f" --namespace "${NS:-default}" --dry-run=client
  fi
done
docker build -t app:latest --build-arg VERSION=1.2.3 .
usql "postgres://user@localhost:5432/db?sslmode=disable" -c 'select count(*) from users;'
function cleanup() { local code=$?; rm -rf ./tmp; return $code; }
trap cleanup EXIT
curl -sSL --max-time 30 https://example.com | jq '.items[] | .name' > out.json
