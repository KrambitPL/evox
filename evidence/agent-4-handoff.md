# Agent 4 handoff — evaluation and release gate

## Delivered

- `evox_api.evaluation`: literal rubric scoring, split leakage detection, frozen candidate
  comparison, three held-out repetitions, aggregation, and explicit hard-gate verification.
- `evox_api.release`: fail-closed promotion/rejection/owner-review receipts plus reversible
  active-version transitions.
- Unit coverage in `packages/api/tests/unit/test_evaluation_release.py`.

## Verification

Run in the agent-4 worktree on 2026-07-24:

```text
uv run --package evox-api pytest packages/api/tests/unit/test_evaluation_release.py
6 passed

uv run --package evox-api ruff check packages/api/src packages/api/tests
All checks passed

uv run --package evox-api pytest packages/api/tests
23 passed
```

## Integration notes

- `compare_candidates` requires a real execution callable and explicit hard-gate checker;
  callers must supply the configured production evaluator and persisted evaluation cases.
- `decide_promotion` is intentionally pure. An adapter must persist its receipt and apply the
  returned active-version change through the repository boundary; no in-memory production store
  or model/provider fallback was added.
