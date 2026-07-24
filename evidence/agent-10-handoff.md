# Agent 10 handoff — real EvoAgentX issue corpus

## Delivered

- `corpus/` contains a provenance-rich 15-case corpus sourced from closed, non-PR
  `EvoAgentX/EvoAgentX` issues: 8 train, 4 dev, and 3 held-out.
- Every hand-reviewable case contains the literal evaluator disposition, required facts,
  acceptable citations, and escalation behavior. All source URLs are canonical upstream
  issue URLs; official EvoAgentX documentation anchors are recorded in `LOCK.json`.
- `scripts/fetch_evoagentx_sources.py` refetches exactly the selected issue numbers and
  fails closed if any resolves to a pull request or non-closed issue. Its latest evidence
  output is `corpus/sources.evoagentx-issues.json`.
- `scripts/validate_corpus.py` validates schema alignment, canonical HTTPS URLs,
  uniqueness, fixed split counts, and cross-split leakage. Its public loader rejects
  held-out data; held-out bodies are isolated in `corpus/release-gate/` for the
  independent release evaluator.

## Verification

```text
uv run ruff check scripts tests/corpus
uv run pytest tests/corpus/test_validate_corpus.py
uv run python scripts/validate_corpus.py
uv run python scripts/fetch_evoagentx_sources.py --output corpus/sources.evoagentx-issues.json
```

The fetch verification returned all 15 locked source numbers:
`87, 90, 93, 102, 112, 199, 209, 212, 213, 223, 224, 231, 233, 234, 238`.
