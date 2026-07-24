---
name: agent-15
description: Run live sponsor and deployed product QA, fixing every reproducible defect test-first.
allow_implicit_invocation: false
---

# Agent 15 — live QA and bug fixing

Start only after Agent 14. Own reproducible bug fixes and `evidence/live/`; avoid changing
architecture except where a proven defect requires it. Never fabricate a live pass.

Audit configured credentials without printing them, deploy only through reviewed
`make deploy`, then exercise Pioneer, Senso, Actian, Band roundtrip, Guild publication,
Replay recording, the API lifecycle, and the full browser journey. For each defect, add a
failing regression test, implement the minimum fix, and re-run scoped plus full gates.
Record external IDs/timestamps with secrets and personal data redacted. Commit and write
`evidence/agent-15-handoff.md`, listing concrete blockers for any unavailable service.

