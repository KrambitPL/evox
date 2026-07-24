---
name: agent-6
description: Implement real Senso document ingestion and cited knowledge retrieval.
allow_implicit_invocation: false
---

# Agent 6 — Senso

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/adapters/senso/` and its
tests. Preserve other agents' work.

Using tests first, implement typed `httpx` calls for upload/ingest, status polling, and
query against configured Senso API (official docs show
`https://apiv2.senso.ai/api/v1`) with `X-API-Key`. Preserve document, source URL,
tenant, freshness, and citation identifiers. Fail closed on missing credentials,
timeouts, malformed citations, or incomplete ingestion. Commit and write
`evidence/agent-6-handoff.md`.

