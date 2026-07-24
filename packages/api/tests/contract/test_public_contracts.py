from datetime import UTC, datetime

from evox_api.domain.contracts import (
    CandidateDiff,
    CandidateReport,
    EvaluationMetrics,
    Job,
    JobStatus,
    JobType,
    ReleaseDecision,
    ReleaseDisposition,
    RunOutcome,
    RunStatus,
)


def test_run_outcome_preserves_weighted_score_components_and_evidence_references() -> None:
    outcome = RunOutcome(
        id="run_001",
        system_id="system_issue_resolver_v1",
        evaluation_case_id="case_001",
        output="The issue is resolved.",
        trace_refs=("s3://evox-traces/run_001.json",),
        evidence_refs=("https://docs.evoagentx.ai/api",),
        score_components={
            "disposition": 1.0,
            "required_facts": 1.0,
            "citation_quality": 1.0,
            "appropriate_escalation": 1.0,
        },
        cost_usd=0.03,
        latency_ms=820,
        status=RunStatus.SUCCEEDED,
        completed_at=datetime.now(UTC),
    )

    assert outcome.overall_score == 1.0


def test_candidate_report_records_baseline_candidate_and_invariant_results() -> None:
    report = CandidateReport(
        id="candidate_001",
        mission_id="mission_issue_resolver",
        baseline_system_id="system_issue_resolver_v1",
        candidate_system_id="system_issue_resolver_v2",
        baseline_metrics=EvaluationMetrics(overall_score=0.71),
        candidate_metrics=EvaluationMetrics(overall_score=0.79),
        repeated_results=(("case_001", (0.78, 0.8, 0.79)),),
        diffs=(CandidateDiff(field="prompts.resolve", before="v1", after="v2"),),
        invariant_results={"immutable_policy_digest_unchanged": True},
        immutable_policy_digest="a" * 64,
    )

    assert report.improvement == 0.08


def test_release_decision_requires_evidence_and_rollback_for_promotion() -> None:
    decision = ReleaseDecision(
        id="release_001",
        candidate_id="candidate_001",
        disposition=ReleaseDisposition.PROMOTE,
        reasons=("All hard gates passed.",),
        evidence_refs=("s3://evox-reports/candidate_001.json",),
        promoted_version="2.0.0",
        rollback_version="1.0.0",
        immutable_policy_digest="b" * 64,
    )

    assert decision.disposition is ReleaseDisposition.PROMOTE


def test_job_is_a_durable_queued_operation_with_explicit_failure_support() -> None:
    job = Job(
        id="job_001",
        type=JobType.FORGE,
        status=JobStatus.QUEUED,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        result_ref=None,
        failure=None,
    )

    assert job.status is JobStatus.QUEUED
