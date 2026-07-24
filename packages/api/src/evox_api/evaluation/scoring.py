from __future__ import annotations

from pydantic import ConfigDict

from evox_api.domain.contracts import (
    ContractModel,
    EvaluationCase,
    ResolutionDisposition,
    ScoreComponents,
)


class IssueResolution(ContractModel):
    """Structured, auditable result supplied by the issue-resolver evaluator."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: ResolutionDisposition
    facts: tuple[str, ...]
    citations: tuple[str, ...]


def score_issue_resolution(case: EvaluationCase, resolution: IssueResolution) -> ScoreComponents:
    """Score literal expected values using the fixed issue-resolver rubric."""
    return ScoreComponents(
        disposition=float(resolution.disposition is case.expected_disposition),
        required_facts=_literal_fraction(case.expected_facts, resolution.facts),
        citation_quality=_literal_fraction(case.expected_citations, resolution.citations),
        appropriate_escalation=float(
            (resolution.disposition is ResolutionDisposition.ESCALATE)
            is (case.expected_disposition is ResolutionDisposition.ESCALATE)
        ),
    )


def _literal_fraction(expected: tuple[str, ...], received: tuple[str, ...]) -> float:
    if not expected:
        return 1.0
    received_values = set(received)
    return sum(value in received_values for value in expected) / len(expected)
