# Agent 10 corpus decisions — 2026-07-24

- The corpus uses 15 closed non-pull-request issues from `EvoAgentX/EvoAgentX`, fetched
  again at implementation time by `scripts/fetch_evoagentx_sources.py` and retained in
  `corpus/sources.evoagentx-issues.json`.
- Public train/dev cases retain only source-grounded excerpts and exact evidence URLs;
  they do not manufacture resolutions, provider support, or source content.
- The locked 8/4/3 split is declared in `corpus/LOCK.json`. Train and dev are the only
  supported optimizer-visible splits. Held-out bodies are in the distinct release gate,
  while the public manifest exposes provenance for audit without a supported optimizer
  loading route.
- Expected dispositions are deliberately explicit evaluator labels, paired with required
  facts, acceptable citations, and fail-closed escalation directions. They are not claims
  that an upstream issue was fixed.
