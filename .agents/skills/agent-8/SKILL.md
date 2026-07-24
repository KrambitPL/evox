---
name: agent-8
description: Implement Band remote human escalation and correlated response worker.
allow_implicit_invocation: false
---

# Agent 8 — Band

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/adapters/band/`, its
persistent worker entry point, and tests. Do not use request-scoped background loops.

Test-first, implement EscalationPort with the official `band-sdk`: create/correlate a
room request, maintain a persistent WebSocket event connection, validate human identity
and response schema, handle expiry/idempotency, and resume the waiting Job. Production
must use the real Band service and fail closed. Commit and write
`evidence/agent-8-handoff.md`.

