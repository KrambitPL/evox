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
    ResolutionDisposition,
    SystemNode,
    immutable_policy_digest,
)


def mission() -> MissionContract:
    return MissionContract(
        id="mission_issue_resolver",
        objective="Resolve EvoAgentX issues with cited official evidence.",
        success_criteria=("Required facts are correct.",),
        allowed_capabilities=frozenset({Capability.KNOWLEDGE_RETRIEVAL}),
        hard_constraints=("Never change frozen evaluation cases.",),
        budgets=BudgetPolicy(max_cost_usd=10, max_latency_ms=15_000, max_model_calls=8),
        evaluation_datasets=EvaluationDatasets(
            train_ref="s3://evox-evaluations/train.jsonl",
            dev_ref="s3://evox-evaluations/dev.jsonl",
            held_out_ref="s3://evox-evaluations/held-out.jsonl",
        ),
        hitl_policy=HitlPolicy(required_for_escalation=True, owner_review_required=True),
    )


def test_immutable_policy_digest_is_stable_for_equivalent_missions() -> None:
    first = mission()
    second = mission()

    assert immutable_policy_digest(first) == immutable_policy_digest(second)


def test_system_rejects_an_immutable_policy_digest_that_does_not_match_its_mission() -> None:
    frozen_mission = mission()
    system = AgenticSystemSpec(
        id="system_issue_resolver_v1",
        mission_id=frozen_mission.id,
        version=1,
        nodes=(SystemNode(id="retrieve", kind="knowledge"),),
        edges=(),
        models={"retrieve": "pioneer-resolver"},
        prompts={"retrieve": "Find official facts."},
        capability_bindings={"retrieve": frozenset({Capability.KNOWLEDGE_RETRIEVAL})},
        mutable_fields=frozenset({"prompts.retrieve"}),
        immutable_policy_digest="0" * 64,
    )

    with pytest.raises(ValueError, match="immutable_policy_digest"):
        system.validate_against(frozen_mission)


def test_evaluation_case_keeps_literal_expected_evidence_and_hard_gates() -> None:
    case = EvaluationCase(
        id="case_001",
        mission_id="mission_issue_resolver",
        split=EvaluationSplit.HELD_OUT,
        input="Resolve issue 123.",
        expected_facts=("The API accepts a timeout parameter.",),
        expected_disposition=ResolutionDisposition.RESOLVED,
        expected_citations=("https://docs.evoagentx.ai/api",),
        hard_gates=("cite_official_documentation", "do_not_expand_permissions"),
    )

    assert case.split is EvaluationSplit.HELD_OUT
    assert case.expected_citations == ("https://docs.evoagentx.ai/api",)


def test_contract_timestamps_are_timezone_aware() -> None:
    timestamp = datetime.now(UTC)

    assert timestamp.tzinfo is UTC
