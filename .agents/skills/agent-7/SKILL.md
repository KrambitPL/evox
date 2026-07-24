---
name: agent-7
description: Implement real Actian VectorAI outcome and failure memory.
allow_implicit_invocation: false
---

# Agent 7 — Actian

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/adapters/actian/` and
tests. Do not modify the domain contracts.

Test-first, implement OutcomeMemoryPort using the official `actian-vectorai-client`
package (`actian_vectorai`). Store run/outcome embeddings with mission, system version,
split, score, failure labels, evidence reference, and retention metadata; retrieve
similar successful and failed cases with filters. Enforce tenant isolation and fail
closed on unavailable server/configuration. Commit and write
`evidence/agent-7-handoff.md`.

