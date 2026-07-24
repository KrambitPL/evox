# AGENTS.md

## Product truth

Production code must use real configured integrations and real persisted state. Never
place mock, fixture, synthetic, demo, placeholder, or silent fallback behavior in a
production path. Test doubles belong only under test directories and may never be
imported by production modules. Missing sponsor configuration must fail closed with an
explicit integration status.

Pioneer is the production model gateway for this repository. Do not add CLIProxyAPI or
silently route to OpenAI, Azure, or another model provider. This project-specific choice
was explicitly approved for the hackathon.

## Engineering rules

- Use test-driven development for behavior: write a failing test, observe the expected
  failure, add the minimum implementation, then refactor while green.
- Python 3.11, `uv`, FastAPI, Pydantic v2, pytest, Ruff. Never run bare `python` or `pip`.
- TypeScript, Next.js App Router, React 19, pnpm 11, Vitest, Playwright. Never use npm,
  yarn, npx, or the legacy Pages Router.
- Keep all Python imports at module scope. Resolve cycles through dependency injection.
- The product depends on ports. Only adapters may import EvoAgentX or sponsor SDKs.
- No generated candidate may mutate hard constraints, permissions, evaluator, frozen
  cases, or budgets. Violation is a fail-closed release rejection.
- Long-running forge, evaluation, and evolution operations return a `202` Job and run
  through the queue boundary.
- Never expose credentials in code, browser bundles, logs, images, or evidence files.

## Git and collaboration

- Remote writes are authorized only to `KrambitPL` or `KramPiotr`. Never write to
  `SentimentAILtd`.
- Each `$agent-N` task owns the files listed in its skill. Use an isolated worktree and
  branch. Do not revert or overwrite other agents' changes.
- Integrators merge reviewed commits only after task-scoped tests pass.
- Before pushing, verify the remote owner. Push only a clean, verified revision.

## Public commands

`make install`, `make test-unit`, `make test-contract`, `make test-integration`,
`make e2e`, `make test-replay`, `make lint`, `make build`, `make verify-live`,
`make smoke`, and `make deploy` are the stable project interface.

