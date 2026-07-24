---
name: agent-5
description: Implement the real fail-closed Pioneer model gateway.
allow_implicit_invocation: false
---

# Agent 5 — Pioneer

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/adapters/pioneer/` and
its tests. Do not add another production model provider. Other agents are concurrent.

Test-first, implement the ModelGateway over Pioneer's OpenAI-compatible endpoint
`https://api.pioneer.ai/v1`, structured-output validation, usage/cost/latency capture,
request correlation, retry limits, redacted errors, and health checks. Pass Pioneer-only
fields deliberately. Missing/invalid configuration must fail closed; no fallback.
Use full wire-shape fixtures only in tests. Commit and write `evidence/agent-5-handoff.md`.

