#!/usr/bin/env bash
set -euo pipefail

readonly base_url=${EVOX_BASE_URL:?Set EVOX_BASE_URL to the deployed Evox endpoint.}
readonly endpoint=${base_url%/}

curl --fail --silent --show-error --max-time 20 "$endpoint/healthz" \
  | jq -e '.status == "ready"' >/dev/null

integration_health=$(
  curl --fail --silent --show-error --max-time 30 "$endpoint/v1/integrations/health"
)

jq -e '
  ["pioneer", "senso", "actian", "band", "guild", "replay"] as $required
  | ($required | all(. as $name | $ARGS.named.health[$name] == "healthy"))
' --argjson health "$integration_health" --null-input >/dev/null

echo "Live readiness and all required integrations are healthy."
