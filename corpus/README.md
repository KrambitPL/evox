# EvoAgentX resolved-issue corpus

This is a deterministic 8 train / 4 dev / 3 held-out evaluation corpus built from
closed, non-pull-request issues in [EvoAgentX/EvoAgentX](https://github.com/EvoAgentX/EvoAgentX).
Every public case keeps its source URL, literal expected disposition, required facts,
acceptable citations, and escalation instruction. The official documentation anchors
are recorded in `LOCK.json`.

Run `uv run python scripts/fetch_evoagentx_sources.py --output /tmp/evoagentx-issues.json`
to retrieve the 15 live source records for review. The fetcher fails if any chosen
record is no longer a closed issue or resolves to a pull request; it never substitutes
another issue.

`heldout-manifest.json` deliberately exposes only provenance and identifiers.
Hand-reviewable held-out bodies are isolated under `release-gate/`; the supported
optimizer loader permits only `train` and `dev` and rejects every held-out loading
attempt. The independent release evaluator is the only consumer of that separate gate.
