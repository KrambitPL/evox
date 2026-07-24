# Agent 7 — Actian outcome-memory handoff

Date: 2026-07-24

## Delivered

- Added `ActianOutcomeMemory`, a real `OutcomeMemoryPort` adapter backed by the official
  `actian-vectorai-client==1.0.1` package (`actian_vectorai`).
- Stores a validated `RunOutcome` alongside its embedding and required metadata: tenant,
  mission, system/version, evaluation split, score, failure labels, evidence references,
  and a retention timestamp.
- Retrieves semantically similar cases through Actian `points.search` with a mandatory
  tenant filter plus allow-listed mission/system/version/split/status/outcome-kind filters.
- Uses stable tenant-scoped UUID point identifiers while retaining the original run ID in
  payload metadata, preventing cross-tenant key collisions.
- Fails closed with `IntegrationUnavailable("actian")` for missing configuration,
  unavailable server/client operations, malformed persisted outcome payloads, and wrong
  embedding dimensions.

## Integration boundary

The frozen `OutcomeMemoryPort` exposes only `RunOutcome`, tenant ID, query, and filters.
It intentionally does not carry mission, system version, evaluation split, retention policy,
or an embedding provider. To avoid inventing metadata or a model fallback, the adapter
requires two explicit production dependencies:

- `embed`: the configured embedding function;
- `context_for_outcome`: the persisted-state resolver for mission/version/split/retention.

Neither has a default or a synthetic implementation. Test doubles are isolated under
`packages/api/tests/unit/adapters/actian/`.

## Verification

```text
make test-unit  # 22 passed
make lint       # All checks passed
```

Focused tests also cover metadata persistence, mandatory tenant isolation, filter rejection,
and unavailable-server fail-closed behavior.
