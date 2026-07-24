---
name: agent-1
description: Bootstrap Evox and freeze its public contracts before parallel implementation.
allow_implicit_invocation: false
---

# Agent 1 — foundation and contracts

Read `AGENTS.md` and the implementation plan completely. You own root build/config
files, `packages/api/src/evox_api/domain/`, `packages/api/src/evox_api/ports/`, contract
tests, and the frozen OpenAPI fixture. You are not alone in the codebase; do not alter
sponsor, UI, infrastructure, or later-agent files.

Using strict TDD, implement all seven public Pydantic contracts, typed identifiers,
state enums, domain errors, immutable-policy digesting, and port Protocols. Create the
FastAPI skeleton and Make targets required by the plan. Ensure test doubles exist only
under tests. Verify unit and contract tests, commit, tag exactly `agent-contracts-v1`,
and write `evidence/agent-1-handoff.md` with commands and commit SHA.

