# Evox agent task catalog

Run a task from a Codex session with `$agent-N`, or select it from `/skills`.
Slash commands named `/agent-N` are not a supported Codex primitive; the `$agent-N`
skill invocation is the stable equivalent.

Every task reads `AGENTS.md` and `docs/plans/2026-07-24-evox-implementation.md`, uses
an isolated `.worktrees/agent-N` branch named `agent-N/<scope>`, practices TDD, commits
only its owned files, and writes `evidence/agent-N-handoff.md`. Agents are not alone in
the repository: fetch/rebase before handoff, accommodate concurrent interfaces, and do
not revert work outside their ownership.

Agent 1 freezes `agent-contracts-v1`. Agents 2–13 branch from that tag. Agent 14 merges
reviewed task commits. Agents 15–16 run only after integration.

