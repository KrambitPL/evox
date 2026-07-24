from __future__ import annotations

from datetime import UTC, datetime

import pytest

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    BudgetPolicy,
    Capability,
    EvaluationCase,
    EvaluationDatasets,
    EvaluationSplit,
    HitlPolicy,
    MissionContract,
    MutableField,
    ResolutionDisposition,
    RunOutcome,
    RunStatus,
    ScoreComponents,
    SystemNode,
    immutable_policy_digest,
)
from evox_api.evaluation.comparison import compare_candidates
from evox_api.evaluation.errors import EvaluationLeakageError
from evox_api.evaluation.isolation import require_isolated_cases
from evox_api.evaluation.scoring import IssueResolution, score_issue_resolution
from evox_api.release.gate import (
    ActiveVersion,
    activate_version,
    decide_promotion,
    rollback_active_version,
)


def mission() -> MissionContract:
    return MissionContract(
        id="mission_issue_resolver",
        objective="Resolve issues using official evidence.",
        success_criteria=("Facts must be accurate.",),
        allowed_capabilities=frozenset({Capability.KNOWLEDGE_RETRIEVAL}),
        hard_constraints=("Do not expand permissions.",),
        budgets=BudgetPolicy(max_cost_usd=10, max_latency_ms=15_000, max_model_calls=8),
        evaluation_datasets=EvaluationDatasets(
            train_ref="s3://evox/train.jsonl",
            dev_ref="s3://evox/dev.jsonl",
            held_out_ref="s3://evox/held-out.jsonl",
        ),
        hitl_policy=HitlPolicy(required_for_escalation=True, owner_review_required=True),
    )


def system(system_id: str, version: int, prompt: str) -> AgenticSystemSpec:
    frozen_mission = mission()
    return AgenticSystemSpec(
        id=system_id,
        mission_id=frozen_mission.id,
        version=version,
        nodes=(SystemNode(id="retrieve", kind="knowledge"),),
        edges=(),
        models={"retrieve": "pioneer-resolver"},
        prompts={"retrieve": prompt},
        capability_bindings={"retrieve": frozenset({Capability.KNOWLEDGE_RETRIEVAL})},
        mutable_fields=frozenset({MutableField.PROMPTS}),
        immutable_policy_digest=immutable_policy_digest(frozen_mission),
    )


def held_out_case(case_id: str = "case_001") -> EvaluationCase:
    return EvaluationCase(
        id=case_id,
        mission_id="mission_issue_resolver",
        split=EvaluationSplit.HELD_OUT,
        input="Why is the request failing?",
        expected_facts=("The timeout must be positive.", "Use the documented endpoint."),
        expected_disposition=ResolutionDisposition.ESCALATE,
        expected_citations=("https://docs.example.test/timeouts",),
        hard_gates=("cite_official_documentation",),
    )


def outcome(system_id: str, case_id: str, score: float) -> RunOutcome:
    return RunOutcome(
        id=f"run_{system_id[-3:]}_{case_id[-3:]}",
        system_id=system_id,
        evaluation_case_id=case_id,
        output="Resolution",
        trace_refs=("trace://run",),
        evidence_refs=("https://docs.example.test/timeouts",),
        score_components=ScoreComponents(
            disposition=score,
            required_facts=score,
            citation_quality=score,
            appropriate_escalation=score,
        ),
        cost_usd=0.01,
        latency_ms=10,
        status=RunStatus.SUCCEEDED,
        completed_at=datetime.now(UTC),
    )


def test_issue_resolver_scores_literal_expected_values_with_weighted_rubric() -> None:
    score = score_issue_resolution(
        held_out_case(),
        IssueResolution(
            disposition=ResolutionDisposition.ESCALATE,
            facts=("The timeout must be positive.",),
            citations=("https://docs.example.test/timeouts",),
        ),
    )

    assert score.disposition == 1
    assert score.required_facts == 0.5
    assert score.citation_quality == 1
    assert score.appropriate_escalation == 1
    assert score.overall == 0.825


def test_isolation_rejects_the_same_evaluation_content_in_two_splits() -> None:
    train_case = held_out_case("case_train").model_copy(update={"split": EvaluationSplit.TRAIN})

    with pytest.raises(EvaluationLeakageError, match="content fingerprint"):
        require_isolated_cases((train_case, held_out_case()))


def test_candidate_comparison_runs_each_held_out_case_exactly_three_times_and_aggregates() -> None:
    baseline = system("system_baseline", 1, "baseline")
    candidate = system("system_candidate", 2, "candidate")
    calls: list[tuple[str, str]] = []

    def run(subject: AgenticSystemSpec, case: EvaluationCase) -> RunOutcome:
        calls.append((subject.id, case.id))
        return outcome(subject.id, case.id, 0.70 if subject.id == baseline.id else 0.80)

    report = compare_candidates(
        candidate_id="candidate_001",
        mission=mission(),
        baseline=baseline,
        candidate=candidate,
        cases=(held_out_case(),),
        run=run,
        diffs=(),
        hard_gate_check=lambda case, result: True,
    )

    assert calls.count((baseline.id, "case_001")) == 3
    assert calls.count((candidate.id, "case_001")) == 3
    assert report.repeated_results == (("case_001", (0.8, 0.8, 0.8)),)
    assert report.baseline_metrics.overall_score == 0.7
    assert report.candidate_metrics.overall_score == 0.8
    assert report.invariant_results["held_out_non_regression"] is True
    assert report.invariant_results["hard_gates_passed"] is True


def test_promotion_requires_five_point_delta_and_all_gate_invariants() -> None:
    baseline = system("system_baseline", 1, "baseline")
    candidate = system("system_candidate", 2, "candidate")
    report = compare_candidates(
        candidate_id="candidate_001",
        mission=mission(),
        baseline=baseline,
        candidate=candidate,
        cases=(held_out_case(),),
        run=lambda subject, case: outcome(
            subject.id, case.id, 0.70 if subject.id == baseline.id else 0.75
        ),
        diffs=(),
        hard_gate_check=lambda case, result: True,
    )

    decision = decide_promotion(
        release_id="release_001",
        report=report,
        baseline=baseline,
        candidate=candidate,
        active_version="system_baseline",
        evidence_refs=("evidence://candidate_001",),
    )

    assert decision.disposition.value == "promote"
    assert decision.approved_system_id == "system_candidate"
    assert decision.rollback_version == "system_baseline"


def test_release_gate_rejects_digest_mismatch_and_rollback_restores_previous_version() -> None:
    baseline = system("system_baseline", 1, "baseline")
    candidate = system("system_candidate", 2, "candidate")
    report = compare_candidates(
        candidate_id="candidate_001",
        mission=mission(),
        baseline=baseline,
        candidate=candidate,
        cases=(held_out_case(),),
        run=lambda subject, case: outcome(subject.id, case.id, 0.9),
        diffs=(),
        hard_gate_check=lambda case, result: True,
    )
    mismatched_candidate = candidate.model_copy(update={"immutable_policy_digest": "a" * 64})

    decision = decide_promotion(
        release_id="release_002",
        report=report,
        baseline=baseline,
        candidate=mismatched_candidate,
        active_version="system_baseline",
        evidence_refs=("evidence://candidate_001",),
    )

    assert decision.disposition.value == "reject"
    active = ActiveVersion(system_id="system_candidate", rollback_system_id="system_baseline")
    assert rollback_active_version(active).system_id == "system_baseline"


def test_qualified_candidate_can_emit_owner_review_receipt_without_activation() -> None:
    baseline = system("system_baseline", 1, "baseline")
    candidate = system("system_candidate", 2, "candidate")
    report = compare_candidates(
        candidate_id="candidate_001",
        mission=mission(),
        baseline=baseline,
        candidate=candidate,
        cases=(held_out_case(),),
        run=lambda subject, case: outcome(
            subject.id, case.id, 0.70 if subject.id == baseline.id else 0.80
        ),
        diffs=(),
        hard_gate_check=lambda case, result: True,
    )

    review = decide_promotion(
        release_id="release_003",
        report=report,
        baseline=baseline,
        candidate=candidate,
        active_version="system_baseline",
        evidence_refs=("evidence://candidate_001",),
        owner_review_required=True,
    )

    assert review.disposition.value == "owner_review"
    with pytest.raises(ValueError, match="Only a promotion"):
        activate_version(ActiveVersion(system_id="system_baseline"), review)
