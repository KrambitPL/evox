# Agent 4 evaluation and release decisions — 2026-07-24

- The issue-resolver rubric is literal and fixed: disposition 35%, required facts 35%,
  citations 20%, and escalation appropriateness 10%. Facts and citations match only
  against their registered evaluation-case values; no semantic or model-based fallback is used.
- Split isolation hashes the complete registered evaluation content (excluding case ID and
  split) and rejects it when it appears across train, development, or held-out splits.
- Candidate comparison freezes deep copies of baseline and candidate specs, runs each held-out
  case exactly three times per subject, aggregates all score components, and verifies that the
  frozen specs did not change during the run.
- Hard-gate evaluation is an explicit required dependency. Missing or false hard-gate evidence
  blocks promotion rather than assuming success.
- Promotion is a pure, auditable gate: it requires an identical immutable-policy digest,
  active baseline identity, all required invariants, three repetitions per held-out case,
  evidence references, and a score delta of at least 0.05. It emits promote, reject, or
  owner-review receipts. Version activation and rollback are explicit reversible transitions;
  persistence remains the responsibility of the repository adapter.
