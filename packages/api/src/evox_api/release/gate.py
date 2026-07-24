from __future__ import annotations

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateReport,
    ReleaseDecision,
    ReleaseDisposition,
    ReleaseId,
    SystemId,
)

PROMOTION_DELTA = 0.05
_REQUIRED_INVARIANTS = frozenset(
    {"held_out_non_regression", "hard_gates_passed", "candidate_frozen"}
)


class ActiveVersion:
    def __init__(self, system_id: SystemId, rollback_system_id: SystemId | None = None) -> None:
        self.system_id = system_id
        self.rollback_system_id = rollback_system_id


def decide_promotion(
    *,
    release_id: ReleaseId,
    report: CandidateReport,
    baseline: AgenticSystemSpec,
    candidate: AgenticSystemSpec,
    active_version: SystemId,
    evidence_refs: tuple[str, ...],
    owner_review_required: bool = False,
) -> ReleaseDecision:
    """Produce an auditable release receipt; unsafe or incomplete evidence fails closed."""
    reasons = _rejection_reasons(report, baseline, candidate, active_version, evidence_refs)
    if reasons:
        return ReleaseDecision(
            id=release_id,
            candidate_id=report.id,
            disposition=ReleaseDisposition.REJECT,
            reasons=tuple(reasons),
            evidence_refs=evidence_refs,
            immutable_policy_digest=report.immutable_policy_digest,
        )
    if owner_review_required:
        return ReleaseDecision(
            id=release_id,
            candidate_id=report.id,
            disposition=ReleaseDisposition.OWNER_REVIEW,
            reasons=("Owner review is required before promotion.",),
            evidence_refs=evidence_refs,
            immutable_policy_digest=report.immutable_policy_digest,
        )
    return ReleaseDecision(
        id=release_id,
        candidate_id=report.id,
        disposition=ReleaseDisposition.PROMOTE,
        reasons=("Candidate satisfied held-out evaluation and all hard release gates.",),
        evidence_refs=evidence_refs,
        approved_system_id=candidate.id,
        promoted_version=candidate.id,
        rollback_version=active_version,
        rollback_release_id=f"rollback_{release_id}",
        immutable_policy_digest=report.immutable_policy_digest,
    )


def activate_version(active: ActiveVersion, decision: ReleaseDecision) -> ActiveVersion:
    if decision.disposition is not ReleaseDisposition.PROMOTE or not decision.approved_system_id:
        raise ValueError("Only a promotion receipt can activate a candidate version.")
    if decision.rollback_version != active.system_id:
        raise ValueError("Promotion receipt rollback version does not match the active version.")
    return ActiveVersion(system_id=decision.approved_system_id, rollback_system_id=active.system_id)


def rollback_active_version(active: ActiveVersion) -> ActiveVersion:
    if active.rollback_system_id is None:
        raise ValueError("Active version has no reversible predecessor.")
    return ActiveVersion(system_id=active.rollback_system_id, rollback_system_id=active.system_id)


def _rejection_reasons(
    report: CandidateReport,
    baseline: AgenticSystemSpec,
    candidate: AgenticSystemSpec,
    active_version: SystemId,
    evidence_refs: tuple[str, ...],
) -> list[str]:
    reasons: list[str] = []
    if not evidence_refs:
        reasons.append("Promotion requires auditable evidence references.")
    if active_version != baseline.id:
        reasons.append("Baseline is not the active version.")
    if report.baseline_system_id != baseline.id or report.candidate_system_id != candidate.id:
        reasons.append("Candidate report system identities do not match the release subjects.")
    digests = {
        report.immutable_policy_digest,
        baseline.immutable_policy_digest,
        candidate.immutable_policy_digest,
    }
    if len(digests) != 1:
        reasons.append("Immutable policy digest differs between report and release subjects.")
    missing_or_failed = sorted(
        invariant
        for invariant in _REQUIRED_INVARIANTS
        if report.invariant_results.get(invariant) is not True
    )
    if missing_or_failed:
        reasons.append(
            "Required release invariants failed or are missing: "
            f"{', '.join(missing_or_failed)}."
        )
    if report.improvement < PROMOTION_DELTA:
        reasons.append("Candidate improvement is below the required 0.05 held-out delta.")
    if not _has_three_repetitions(report):
        reasons.append(
            "Candidate report does not contain exactly three held-out repetitions per case."
        )
    return reasons


def _has_three_repetitions(report: CandidateReport) -> bool:
    return bool(report.repeated_results) and all(
        len(scores) == 3 for _, scores in report.repeated_results
    )
