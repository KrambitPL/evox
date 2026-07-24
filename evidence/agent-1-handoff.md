# Agent 1 handoff

Contract implementation commit: `30686f616508c9b2c2e1a65792c8e9841635935f`

Red commands observed before implementation:

- `uv run --package evox-api pytest packages/api/tests/contract/test_domain_contracts.py` — failed because `evox_api` did not exist.
- `uv run --package evox-api pytest packages/api/tests/contract` — failed because `evox_api` did not exist.
- `uv run --package evox-api pytest packages/api/tests/contract` — after core code, failed because the frozen OpenAPI fixture did not exist.

Green verification:

- `make install`
- `make test-unit` — 11 passed.
- `make test-contract` — 11 passed.
- `make lint` — all checks passed.
- `pnpm install --frozen-lockfile` — completed successfully.
- `git diff --check` — completed successfully.

Review remediation verification:

- `uv run --package evox-api pytest packages/api/tests/contract` initially failed because the publication release gate was absent.
- `make test-unit` — 18 passed.
- `make test-contract` — 18 passed.
- `make lint` — all checks passed.

The contract now rejects capabilities outside mission authority, limits mutation targets to `prompts` and `sequential_edges`, requires an approved release bound to its system before publication, serializes immutable-policy violations as `409`, and scopes Senso/Actian port calls by tenant and filters.

Concerns:

- The API skeleton intentionally fails closed with a structured `503` until the persistence, queue, and sponsor adapter lanes provide configured real integrations.
- `test-integration`, `e2e`, `test-replay`, `build`, `verify-live`, `smoke`, and `deploy` explicitly fail until their owning lanes implement them; they do not claim success.
