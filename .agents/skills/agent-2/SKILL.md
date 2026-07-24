---
name: agent-2
description: Implement durable repositories and the asynchronous job boundary.
allow_implicit_invocation: false
---

# Agent 2 — persistence and jobs

Start from `agent-contracts-v1`. Read `AGENTS.md` and the plan. You own
`packages/api/src/evox_api/persistence/`, `jobs/`, and matching tests. You are not alone;
preserve frozen contracts and never revert other edits.

Test-first, implement DynamoDB repositories, S3 evidence/artifact storage, SQS enqueue
and worker dispatch, optimistic concurrency, idempotency keys, and explicit job failure
records. Keep in-memory fakes exclusively in tests. Production constructors must fail
closed on missing AWS configuration. Add repository/job contract tests, run them, commit,
and record `evidence/agent-2-handoff.md`.

