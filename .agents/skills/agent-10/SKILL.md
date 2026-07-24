---
name: agent-10
description: Build and lock the real resolved EvoAgentX issue evaluation corpus.
allow_implicit_invocation: false
---

# Agent 10 — real issue corpus

Start from `agent-contracts-v1`. Own `corpus/`, corpus fetch/validation scripts, and
their tests. Never invent or silently substitute issue content.

Fetch at least 15 resolved issues from the real EvoAgentX repository plus relevant
official documentation. Create provenance-rich, hand-reviewable cases with literal
expected disposition, required facts, acceptable citations, and escalation behavior.
Lock a deterministic 8 train / 4 dev / 3 held-out split; encrypt or separately gate
held-out loading so optimizer code cannot access it. Tests validate URLs, uniqueness,
schema, split counts, and leakage. Commit and write `evidence/agent-10-handoff.md`.

