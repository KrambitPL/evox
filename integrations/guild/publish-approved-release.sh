#!/usr/bin/env bash
set -euo pipefail

require_value() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "missing required ${name}" >&2
    exit 2
  fi
}

require_value GUILD_WORKSPACE_ID
require_value EVOX_RELEASE_ID
require_value EVOX_APPROVED_RELEASE_ID
require_value EVOX_IMMUTABLE_POLICY_DIGEST

if [[ "$EVOX_RELEASE_ID" != "$EVOX_APPROVED_RELEASE_ID" ]]; then
  echo "refusing publication: release is not the approved immutable release ID" >&2
  exit 2
fi

if [[ ! "$EVOX_IMMUTABLE_POLICY_DIGEST" =~ ^[a-f0-9]{64}$ ]]; then
  echo "refusing publication: immutable policy digest is invalid" >&2
  exit 2
fi

# The Guild CLI owns authentication and credential storage. Never accept or print a token here.
guild auth status >/dev/null
guild agent save -A --wait --publish --message "Evox approved release ${EVOX_RELEASE_ID}"
guild agent get
guild agent versions --limit 1
