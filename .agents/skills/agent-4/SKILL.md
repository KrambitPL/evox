---
name: agent-4
description: Implement scoring, data isolation, candidate comparison, promotion, and rollback.
allow_implicit_invocation: false
---

# Agent 4 — evaluation and release gate

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/evaluation/`,
`release/`, and tests. Preserve interfaces; do not touch sponsor adapters or UI.

Test-first, implement literal issue-resolver scoring (35 disposition, 35 facts,
20 citations, 10 escalation), split isolation, candidate freeze, three held-out
repetitions, aggregation, and leakage detection. Promotion requires delta >= 0.05,
no held-out or hard-gate regression, and identical immutable digest. Emit auditable
promote/reject/owner-review receipts and reversible active-version changes. Commit and
write `evidence/agent-4-handoff.md`.

