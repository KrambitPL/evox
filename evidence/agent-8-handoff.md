# Agent 8 handoff — Band escalation

Commit scope: Band adapter, persistent WebSocket worker entry point, queue
resumer, tests, and the pinned `band-sdk` dependency.

Verification completed:

- `make test-unit` — 22 passed
- `make lint` — passed
- `git diff --check` — passed
- Live Band registration — agent `6eb62abe-f880-44d5-9ae2-2b8dc0f42b5c`
  created through the Human API and its one-time key validated through
  `/api/v1/agent/me` on 2026-07-25; no secret value was recorded in evidence.

Operational composition calls `run_worker(database_path=..., jobs=..., queue=...)`
from `evox_api.adapters.band.worker` with real persistence and queue adapters.
It fails closed when required Band environment configuration is unavailable.

The human REST credential is provisioning-only. The runtime receives the generated,
agent-scoped `EVOX_BAND_API_KEY`; it must never receive the human key.
