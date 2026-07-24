---
name: agent-9
description: Implement Guild.ai publication and active-release governance.
allow_implicit_invocation: false
---

# Agent 9 — Guild.ai

Start from `agent-contracts-v1`. Own `integrations/guild/`,
`packages/api/src/evox_api/adapters/guild/`, and tests. Work around concurrent changes.

Test-first, build a versioned Issue Resolver/Release Inspector Guild agent and a typed
PublicationPort. Publish only approved immutable release IDs, expose active version and
rollback linkage, preserve credential policy, and reconcile remote publication state.
Use `@guildai/agents-sdk` only inside its supported runtime and the official CLI for
packaging. Fail closed on missing configuration. Commit and write
`evidence/agent-9-handoff.md`.

