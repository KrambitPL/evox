#!/usr/bin/env bash
set -euo pipefail

readonly base_url=${EVOX_BASE_URL:?Set EVOX_BASE_URL to the deployed Evox endpoint.}
readonly endpoint=${base_url%/}

curl --fail --silent --show-error --max-time 20 "$endpoint/healthz" \
  | jq -e '.status == "ready"' >/dev/null

web_response=$(curl --fail --silent --show-error --max-time 30 "$endpoint/")
test -n "$web_response"

echo "Independent API readiness and web endpoint smoke checks passed."
