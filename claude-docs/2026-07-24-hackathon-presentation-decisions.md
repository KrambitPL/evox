# Evox hackathon presentation decisions — 2026-07-24

## Artifact

- Deliverable: `outputs/evox-swarmhack-pitch.pptx`
- Format: 16:9 PowerPoint, 10 slides, with presenter notes on every slide.
- Intended delivery: a concise hackathon pitch that can be presented in roughly three minutes while retaining enough architectural evidence for follow-up judging.

## Source and visual system

- Product claims were grounded in the Evox repository: `MISSION.md`, `README.md`, the implementation plan, architecture research, domain contracts, API behavior, and agent handoffs.
- Outreach narrative context and examples came from `../outreach-research`, including its sales-enablement and copywriting skills.
- The exact visual reference was the current GORGOS investor deck at `../outreach-research/cmpANY/cmpANY-pitch-deck/public/downloads/revisions/91c5e2adc9fc0f21a40c/gorgos-investor-deck-v11.pptx`.
- The deck deliberately follows that reference's editorial rail, Space Grotesk typography, dark navy/cream alternation, teal system color, and orange gate/failure color. Template fidelity was checked after export.
- The title visual is a real Quick Look rendering of this repository's `MISSION.md`, not a fabricated product screenshot.

## Narrative choices

1. Open with the product promise: measurable mission to governed agent evolution.
2. Establish the release gap between candidate generation and earned authority.
3. Show why mutable evaluators, permissions, or held-out evidence invalidate apparent gains.
4. Explain the owner-facing lifecycle and offline-only evolution model.
5. Define the immutable constitution and the narrow mutable workflow surface.
6. Make the proof falsifiable through the locked issue-resolver corpus and defined release threshold.
7. Show sponsor boundaries and the fail-closed integration contract.
8. Separate verified implementation truth from target architecture.
9. Generalize from the first resolver to any measurable mission.
10. Close on one mission, one candidate, one proof.

## Truth boundaries

- The committed 15-case corpus is labeled as existing code; repeated held-out runs and the `+0.05` promotion threshold are labeled as evaluation requirements, not achieved performance.
- The current-state slide records revision `f5da248`: 45 unit tests, 24 contract tests, 4 integration tests, 5 corpus tests, 4 web unit tests, lint green, a successful production web build, and valid Terraform configuration.
- The deck states that persistence/queue, the locked 15-case corpus, sponsor adapters, cockpit, and AWS lane are code-integrated, while production job dispatch has no handlers and end-to-end resolver, public deployment, live sponsor/Replay, and promotion evidence remain pending.
- Operational `409` and `503` behavior is presented as explicit fail-closed behavior, not a completed product funnel.
- No production mock, synthetic fallback, silent provider substitution, customer result, or fabricated sponsor integration is claimed.
- Sponsor outputs are framed as required live evidence, not as proof merely because their fail-closed adapters are integrated.

## Verification

- `slides_test.py`: passed with no overflow detected.
- PowerPoint-compatible rendering: all 10 slides rendered and visually inspected at full size.
- Template-fidelity check: passed with zero issues.
- Independent read-only review identified and removed language that could imply live sponsor, promotion, or deployment evidence. After the remote `main` advanced by 30 integration commits, the deck was re-audited against the new code and updated to distinguish integrated local build evidence from still-missing live proof.
- Repository verification commands are run again immediately before commit and push.

## Tradeoffs

- The deck prioritizes evidence and release governance over a broad feature tour because this is Evox's clearest differentiation and the strongest truth-preserving hackathon story.
- Dense architecture slides retain the source deck's editorial system, while wording and typography were tightened where needed to remain legible in both artifact-tool and LibreOffice/PowerPoint-compatible rendering.
- Speaker notes carry detailed sourcing and talk tracks so the visible slides remain concise.
