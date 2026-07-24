# Simple Evox explainer deck decisions — 2026-07-25

## Artifact

- Deliverable: `outputs/evox-simple-explainer.pptx`
- Format: editable 16:9 PowerPoint with five slides and presenter notes on every slide.
- Purpose: explain Evox to hackathon judges in plain language without relying on the earlier GORGOS visual system or diagrams.

## Narrative

The deck reduces Evox to one causal sequence:

1. A user supplies a problem, success criteria, evidence, and boundaries.
2. Evox turns the mission into an agentic workflow.
3. Every result is measured against the same success criteria.
4. Outcomes become evidence for a new candidate.
5. A candidate becomes active only when it proves better without changing the rules.

The closing distinction is: the system learns how to work; the owner keeps control of what “better” means.

## Visual decisions

- Created from scratch; no GORGOS slide frames, layouts, diagrams, imagery, typography, or theme were reused.
- Used a single warm-white canvas, large Aptos typography, blue for system flow, green for proven success, orange for failure, and dark navy for fixed rules.
- Kept each slide to one claim and one simple visual structure.
- Used native editable PowerPoint objects only; no screenshots or decorative stock imagery.

## Truth boundaries

- The deck explains the intended Evox product model rather than claiming live performance or completed production operation.
- Success criteria, permissions, evaluator, and other authority boundaries remain fixed while candidate workflows may change.
- Candidate promotion is described as evidence-gated; no fabricated benchmark, deployment, sponsor, or customer result is shown.
- Product language is grounded in `MISSION.md` and `README.md`.

## Verification

- All five slides rendered successfully through the PowerPoint-compatible rendering path.
- Every rendered slide was inspected at full size.
- `slides_test.py` passed with no overflow detected.
- The exported package contains presenter notes for all five slides and passes ZIP integrity validation.
