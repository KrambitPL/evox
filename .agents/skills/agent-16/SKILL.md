---
name: agent-16
description: Perform final review, release verification, evidence report, email, and authorized push.
allow_implicit_invocation: false
---

# Agent 16 — release and handoff

Start only after Agent 15. Own final release documentation and evidence manifests. Do not
weaken gates to make a release pass.

Review requirements line by line, inspect diffs and dependency/security findings, run
all fresh verification commands, validate the deployed SHA and rollback, and distinguish
verified, blocked, and unverified claims. Write the dated decision/tradeoff note under
`claude-docs/`, the final Markdown report, and send it to `piotr.kram7@gmail.com` through
the real configured `mail-integrations` tooling. Before push, verify remote owner is
KrambitPL or KramPiotr, tree is clean, and the exact tested SHA is on `main`. Never write
to SentimentAILtd. Write `evidence/agent-16-handoff.md` with email and push evidence.

