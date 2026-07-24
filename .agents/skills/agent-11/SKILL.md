---
name: agent-11
description: Build the complete Next.js owner cockpit for the governed learning loop.
allow_implicit_invocation: false
---

# Agent 11 — web cockpit

Start from `agent-contracts-v1`. Own `packages/web/` except Replay-specific e2e setup.
Use pnpm and the App Router. Other agents are working; consume frozen API types without
changing them.

Test-first, implement one polished responsive cockpit with Define, System, Trial, Gate,
and Operate states. Define captures objective, criteria, capabilities, constraints,
datasets, budget, and HITL. System shows generated graph and mutable/immutable rails.
Trial compares baseline/candidate evidence. Gate shows the decision receipt and explicit
promotion. Operate shows active version, feedback, failures, and rollback. Add a truthful
six-sponsor health strip and accessible loading/error/empty states. No synthetic
production data. Commit and write `evidence/agent-11-handoff.md`.

