from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import evoagentx
import pytest

from evox_api.adapters.evoagentx.engine import (
    EvoAgentXEngine,
    EvolutionResult,
    ExecutionResult,
    SequentialWorkflow,
)
from evox_api.domain.contracts import (
    BudgetPolicy,
    CandidateReport,
    Capability,
    EvaluationDatasets,
    EvaluationMetrics,
    HitlPolicy,
    MissionContract,
    MutableField,
    RunStatus,
)
from evox_api.domain.errors import ImmutablePolicyViolation, IntegrationUnavailable


def mission() -> MissionContract:
    return MissionContract(
        id="claims-triage",
        objective="Resolve claims correctly.",
        success_criteria=("Correct disposition",),
        allowed_capabilities=frozenset({Capability.KNOWLEDGE_RETRIEVAL}),
        hard_constraints=("Never invent a citation.",),
        budgets=BudgetPolicy(max_cost_usd=2, max_latency_ms=2_000, max_model_calls=4),
        evaluation_datasets=EvaluationDatasets(
            train_ref="train-v1", dev_ref="dev-v1", held_out_ref="held-v1"
        ),
        hitl_policy=HitlPolicy(required_for_escalation=True, owner_review_required=True),
    )


def report(system_id: str, digest: str) -> CandidateReport:
    metrics = EvaluationMetrics(overall_score=0.8)
    return CandidateReport(
        id="candidate-001",
        mission_id="claims-triage",
        baseline_system_id=system_id,
        candidate_system_id="candidate-system",
        baseline_metrics=metrics,
        candidate_metrics=metrics,
        repeated_results=(),
        diffs=(),
        invariant_results={"policy": True},
        immutable_policy_digest=digest,
    )


@dataclass
class FakeBackend:
    workflow: SequentialWorkflow
    evolution: EvolutionResult | None = None

    async def generate(self, received_mission: MissionContract) -> SequentialWorkflow:
        assert received_mission.id == "claims-triage"
        return self.workflow

    async def execute(self, system_id: str, input_text: str) -> ExecutionResult:
        assert system_id == "claims-triage-system"
        assert input_text == "Where is my claim?"
        return ExecutionResult(
            output="Your claim is under review.",
            trace_refs=("trace://run-001",),
            evidence_refs=("evidence://claim-1",),
            cost_usd=0.03,
            latency_ms=120,
            status=RunStatus.SUCCEEDED,
            completed_at=datetime(2026, 7, 24, tzinfo=UTC),
        )

    async def sew(
        self, system_id: str, current: SequentialWorkflow, candidate: CandidateReport
    ) -> EvolutionResult:
        assert system_id == "claims-triage-system"
        assert candidate.candidate_system_id == "candidate-system"
        assert current == self.workflow
        assert self.evolution is not None
        return self.evolution


def workflow() -> SequentialWorkflow:
    return SequentialWorkflow(
        node_ids=("retrieve-claim", "resolve-claim"),
        prompts={
            "retrieve-claim": "Find evidence for {input}.",
            "resolve-claim": "Resolve using the evidence.",
        },
        models={"retrieve-claim": "pioneer/claims", "resolve-claim": "pioneer/claims"},
        capability_bindings={
            "retrieve-claim": frozenset({Capability.KNOWLEDGE_RETRIEVAL}),
            "resolve-claim": frozenset(),
        },
    )


def test_pins_real_evoagentx_014() -> None:
    assert evoagentx.__version__ == "0.1.4"


@pytest.mark.asyncio
async def test_forge_maps_mission_to_a_sequential_system_spec() -> None:
    engine = EvoAgentXEngine(backend=FakeBackend(workflow()))

    system = await engine.forge(mission())

    assert system.id == "claims-triage-system"
    assert [node.id for node in system.nodes] == ["retrieve-claim", "resolve-claim"]
    assert [(edge.source, edge.target) for edge in system.edges] == [
        ("retrieve-claim", "resolve-claim")
    ]
    assert system.mutable_fields == frozenset({MutableField.PROMPTS, MutableField.SEQUENTIAL_EDGES})
    assert system.immutable_policy_digest == mission().immutable_policy_digest


@pytest.mark.asyncio
async def test_run_maps_execution_evidence_to_run_outcome() -> None:
    engine = EvoAgentXEngine(backend=FakeBackend(workflow()))
    system = await engine.forge(mission())

    outcome = await engine.run(system, "Where is my claim?")

    assert outcome.output == "Your claim is under review."
    assert outcome.trace_refs == ("trace://run-001",)
    assert outcome.evidence_refs == ("evidence://claim-1",)
    assert outcome.status is RunStatus.SUCCEEDED
    assert outcome.cost_usd == 0.03


@pytest.mark.asyncio
async def test_evolve_allows_only_prompts_and_sequential_ordering() -> None:
    base_workflow = workflow()
    evolved = SequentialWorkflow(
        node_ids=("resolve-claim", "retrieve-claim"),
        prompts={**base_workflow.prompts, "resolve-claim": "Resolve faithfully using evidence."},
        models=base_workflow.models,
        capability_bindings=base_workflow.capability_bindings,
    )
    engine = EvoAgentXEngine(
        backend=FakeBackend(
            base_workflow,
            EvolutionResult(
                workflow=evolved,
                changed_fields=frozenset({"prompts", "sequential_edges"}),
            ),
        )
    )
    system = await engine.forge(mission())

    candidate = await engine.evolve(system, report(system.id, system.immutable_policy_digest))

    assert [node.id for node in candidate.nodes] == ["resolve-claim", "retrieve-claim"]
    assert candidate.prompts["resolve-claim"] == "Resolve faithfully using evidence."
    assert candidate.immutable_policy_digest == system.immutable_policy_digest
    assert candidate.capability_bindings == system.capability_bindings


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "changed_field",
    [
        "permissions",
        "hard_constraints",
        "budgets",
        "evaluator",
        "immutable_policy_digest",
        "aflow_code",
    ],
)
async def test_evolve_rejects_all_non_mutable_optimizer_changes(changed_field: str) -> None:
    base_workflow = workflow()
    engine = EvoAgentXEngine(
        backend=FakeBackend(
            base_workflow,
            EvolutionResult(workflow=base_workflow, changed_fields=frozenset({changed_field})),
        )
    )
    system = await engine.forge(mission())

    with pytest.raises(ImmutablePolicyViolation):
        await engine.evolve(system, report(system.id, system.immutable_policy_digest))


@pytest.mark.asyncio
async def test_evolve_rejects_a_mutation_of_immutable_system_configuration() -> None:
    base_workflow = workflow()
    mutated_capabilities = {
        **base_workflow.capability_bindings,
        "resolve-claim": frozenset({Capability.MODEL_INFERENCE}),
    }
    engine = EvoAgentXEngine(
        backend=FakeBackend(
            base_workflow,
            EvolutionResult(
                workflow=SequentialWorkflow(
                    node_ids=base_workflow.node_ids,
                    prompts=base_workflow.prompts,
                    models=base_workflow.models,
                    capability_bindings=mutated_capabilities,
                ),
                changed_fields=frozenset({"prompts"}),
            ),
        )
    )
    system = await engine.forge(mission())

    with pytest.raises(ImmutablePolicyViolation):
        await engine.evolve(system, report(system.id, system.immutable_policy_digest))


def test_requires_a_configured_real_backend() -> None:
    with pytest.raises(IntegrationUnavailable):
        EvoAgentXEngine()
