---
name: agent-3
description: Adapt pinned EvoAgentX generation, execution, and SEW evolution behind ports.
allow_implicit_invocation: false
---

# Agent 3 — EvoAgentX engine adapter

Start from `agent-contracts-v1`. Own `packages/api/src/evox_api/adapters/evoagentx/` and
its tests. Do not expose EvoAgentX internals through domain contracts or modify unrelated
files. Other agents are working concurrently.

Pin and verify EvoAgentX `0.1.4`. With tests first, map MissionContract to sequential
workflow generation, map workflow execution to RunOutcome evidence, and run SEW only on
mutable prompts/ordering. Reject any optimizer output that changes permissions, hard
constraints, budgets, evaluator, or immutable digest. No AFlow/code mutation. Tests may
use isolated substitutes; production imports the real package and fails explicitly.
Commit and write `evidence/agent-3-handoff.md`.

