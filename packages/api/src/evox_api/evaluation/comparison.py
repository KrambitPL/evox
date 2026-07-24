from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateDiff,
    CandidateId,
    CandidateReport,
    EvaluationCase,
    EvaluationMetrics,
    EvaluationSplit,
    MissionContract,
    RunOutcome,
)

from .errors import CandidateFreezeError
from .isolation import require_isolated_cases

REPETITIONS = 3
RunEvaluator = Callable[[AgenticSystemSpec, EvaluationCase], RunOutcome]
HardGateCheck = Callable[[EvaluationCase, RunOutcome], bool]


def compare_candidates(
    *,
    candidate_id: CandidateId,
    mission: MissionContract,
    baseline: AgenticSystemSpec,
    candidate: AgenticSystemSpec,
    cases: tuple[EvaluationCase, ...],
    run: RunEvaluator,
    diffs: tuple[CandidateDiff, ...],
    hard_gate_check: HardGateCheck,
    validate_systems: bool = True,
) -> CandidateReport:
    """Freeze two candidates, then compare exactly three held-out executions per case."""
    frozen = _freeze_candidate(mission, baseline, candidate, cases, validate_systems)
    baseline_outcomes = _run_repeatedly(frozen.baseline, frozen.held_out_cases, run)
    candidate_outcomes = _run_repeatedly(frozen.candidate, frozen.held_out_cases, run)
    _require_unchanged(frozen.baseline_digest, frozen.baseline, "baseline")
    _require_unchanged(frozen.candidate_digest, frozen.candidate, "candidate")

    baseline_metrics = _aggregate_metrics(baseline_outcomes)
    candidate_metrics = _aggregate_metrics(candidate_outcomes)
    hard_gates_passed = all(
        hard_gate_check(case, outcome)
        for case, outcomes in candidate_outcomes
        for outcome in outcomes
    )
    repeated_results = tuple(
        (case.id, tuple(outcome.overall_score for outcome in outcomes))
        for case, outcomes in candidate_outcomes
    )
    return CandidateReport(
        id=candidate_id,
        mission_id=mission.id,
        baseline_system_id=baseline.id,
        candidate_system_id=candidate.id,
        baseline_metrics=baseline_metrics,
        candidate_metrics=candidate_metrics,
        repeated_results=repeated_results,
        diffs=diffs,
        invariant_results={
            "held_out_non_regression": candidate_metrics.overall_score
            >= baseline_metrics.overall_score,
            "hard_gates_passed": hard_gates_passed,
            "candidate_frozen": True,
        },
        immutable_policy_digest=mission.immutable_policy_digest,
    )


class _FrozenCandidate:
    def __init__(
        self,
        baseline: AgenticSystemSpec,
        candidate: AgenticSystemSpec,
        held_out_cases: tuple[EvaluationCase, ...],
    ) -> None:
        self.baseline = baseline
        self.candidate = candidate
        self.held_out_cases = held_out_cases
        self.baseline_digest = _system_digest(baseline)
        self.candidate_digest = _system_digest(candidate)


def _freeze_candidate(
    mission: MissionContract,
    baseline: AgenticSystemSpec,
    candidate: AgenticSystemSpec,
    cases: tuple[EvaluationCase, ...],
    validate_systems: bool,
) -> _FrozenCandidate:
    if baseline.id == candidate.id:
        raise CandidateFreezeError("Baseline and candidate must be distinct systems.", {})
    if validate_systems:
        baseline.validate_against(mission)
        candidate.validate_against(mission)
    if baseline.immutable_policy_digest != candidate.immutable_policy_digest:
        raise CandidateFreezeError("Candidate policy digest differs from the baseline.", {})
    require_isolated_cases(cases)
    held_out_cases = tuple(case for case in cases if case.split is EvaluationSplit.HELD_OUT)
    if not held_out_cases:
        raise CandidateFreezeError("Candidate comparison requires held-out cases.", {})
    if any(case.mission_id != mission.id for case in held_out_cases):
        raise CandidateFreezeError("Held-out cases belong to another mission.", {})
    return _FrozenCandidate(
        baseline.model_copy(deep=True), candidate.model_copy(deep=True), held_out_cases
    )


def _run_repeatedly(
    system: AgenticSystemSpec, cases: tuple[EvaluationCase, ...], run: RunEvaluator
) -> tuple[tuple[EvaluationCase, tuple[RunOutcome, ...]], ...]:
    results: list[tuple[EvaluationCase, tuple[RunOutcome, ...]]] = []
    for case in cases:
        outcomes = tuple(run(system, case) for _ in range(REPETITIONS))
        if any(
            outcome.system_id != system.id or outcome.evaluation_case_id != case.id
            for outcome in outcomes
        ):
            raise CandidateFreezeError(
                "Evaluation outcome does not match its frozen subject or case.", {}
            )
        results.append((case, outcomes))
    return tuple(results)


def _aggregate_metrics(
    results: tuple[tuple[EvaluationCase, tuple[RunOutcome, ...]], ...]
) -> EvaluationMetrics:
    outcomes = tuple(outcome for _, repeated in results for outcome in repeated)
    if not outcomes:
        raise CandidateFreezeError("Cannot aggregate an empty held-out evaluation.", {})
    return EvaluationMetrics(
        overall_score=_mean(outcome.overall_score for outcome in outcomes),
        disposition_score=_mean(outcome.score_components.disposition for outcome in outcomes),
        required_facts_score=_mean(outcome.score_components.required_facts for outcome in outcomes),
        citation_quality_score=_mean(
            outcome.score_components.citation_quality for outcome in outcomes
        ),
        appropriate_escalation_score=_mean(
            outcome.score_components.appropriate_escalation for outcome in outcomes
        ),
    )


def _mean(values: Iterable[float]) -> float:
    values_tuple = tuple(values)
    return round(sum(values_tuple) / len(values_tuple), 8)


def _require_unchanged(expected_digest: str, system: AgenticSystemSpec, role: str) -> None:
    if _system_digest(system) != expected_digest:
        raise CandidateFreezeError(f"Frozen {role} system changed during evaluation.", {})


def _system_digest(system: AgenticSystemSpec) -> str:
    payload = json.dumps(system.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
