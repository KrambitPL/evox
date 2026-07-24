#!/usr/bin/env bash
set -euo pipefail

readonly base_url=${EVOX_BASE_URL:?Set EVOX_BASE_URL to the deployed Evox endpoint.}
readonly endpoint=${base_url%/}

curl --fail --silent --show-error --max-time 20 "$endpoint/healthz" \
  | jq -e '.status == "ready"' >/dev/null

integration_health=$(
  curl --fail --silent --show-error --max-time 30 "$endpoint/v1/integrations/health"
)

if test "${EVOX_ALLOW_UNAVAILABLE_SPONSORS:-false}" = "true"; then
  jq -e '
    (.services | map({key: (.name | ascii_downcase), value: .status}) | from_entries) as $health
    | $health.pioneer == "healthy"
      and $health.senso == "healthy"
      and ($health.actian == "healthy" or $health.actian == "unavailable")
      and ($health.band == "healthy" or $health.band == "unavailable")
      and ($health["guild.ai"] == "healthy" or $health["guild.ai"] == "degraded" or $health["guild.ai"] == "unavailable")
      and ($health["replay.io"] == "healthy" or $health["replay.io"] == "degraded")
  ' <<<"$integration_health" >/dev/null
else
  jq -e '
    (.services | map({key: (.name | ascii_downcase), value: .status}) | from_entries) as $health
    | ["pioneer", "senso", "actian", "band", "guild.ai", "replay.io"]
    | all(. as $name | $health[$name] == "healthy")
  ' <<<"$integration_health" >/dev/null
fi

echo "Live readiness and configured integration policy passed."
