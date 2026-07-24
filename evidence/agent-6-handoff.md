# Agent 6 — Senso handoff

Date: 2026-07-24

## Delivered

- Added the real `SensoAdapter` under `packages/api/src/evox_api/adapters/senso/`.
- Uses the configured `https://apiv2.senso.ai/api/v1` route and `X-API-Key` authentication.
- Implements the documented Senso lifecycle: request presigned upload URL, upload bytes,
  resolve the KB node, then poll its processing status until `complete`.
- Implements Senso search with tenant-scoped filters and returns port-level knowledge results.
- Preserves citation ID, document ID, source URL, source title, tenant, and freshness in
  `KnowledgeCitation`.
- Fails closed for absent API keys, HTTP timeouts/errors, malformed JSON or citations,
  tenant mismatches, missing KB nodes, and every non-complete ingestion terminal/timeout state.

## Verification

- `uv run ruff check packages/api/src/evox_api/adapters packages/api/src/evox_api/ports/sponsors.py packages/api/tests/unit/adapters/senso/test_adapter.py`
- `uv run pytest packages/api/tests` — 23 passed
- `git diff --check`

## Source contract

The implementation follows Senso's public developer documentation for the organization KB
upload, KB node lookup, and processing-status poll flow. No local retrieval, synthetic
content, provider fallback, or implicit tenant substitution is present.
