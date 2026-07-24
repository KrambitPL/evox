# Agent 8 handoff — Band escalation

Commit scope: Band adapter, persistent WebSocket worker entry point, queue
resumer, tests, and the pinned `band-sdk` dependency.

Verification completed:

- `make test-unit` — 22 passed
- `make lint` — passed
- `git diff --check` — passed

Operational composition calls `run_worker(database_path=..., jobs=..., queue=...)`
from `evox_api.adapters.band.worker` with real persistence and queue adapters.
It fails closed when required Band environment configuration is unavailable.
