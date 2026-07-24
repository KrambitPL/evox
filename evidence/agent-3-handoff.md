# Agent 3 handoff — 2026-07-24

## Delivered

- Pinned the API package to `evoagentx==0.1.4` and verify its installed version in
  adapter tests.
- Added the private EvoAgentX adapter boundary at
  `packages/api/src/evox_api/adapters/evoagentx/`. Domain contracts and workflow
  ports do not import EvoAgentX.
- `EvoAgentXEngine` maps a mission-generated sequential workflow into an
  `AgenticSystemSpec`, maps execution receipts into `RunOutcome` evidence, and
  applies SEW outputs only after an immutable-policy gate.
- Evolution accepts only prompt changes and reordering of existing sequential
  nodes. It rejects permissions/capabilities, hard constraints, budgets,
  evaluator changes, immutable digests, AFlow/code changes, model changes, and
  node addition/removal.
- The engine has no implicit backend, model, provider, or fake fallback. Missing
  EvoAgentX runtime composition raises `IntegrationUnavailable`.

## Design notes

EvoAgentX 0.1.4 imports optional tool integrations only when its deeper workflow
modules are activated. The adapter therefore imports the real pinned distribution
at startup but accepts a configured private backend for its runtime operations.
This avoids activating unrelated browser/Docker/tool dependencies in API startup;
the composition layer must provide the real Pioneer-backed EvoAgentX backend.
Tests use only an isolated in-test backend substitute.

## Verification

```text
uv run --package evox-api pytest packages/api/tests/unit/adapters/evoagentx/test_engine.py -q
12 passed

make test-unit
30 passed

make lint
All checks passed!
```
