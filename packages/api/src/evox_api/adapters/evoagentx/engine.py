"""Fail-closed EvoAgentX adapter.

EvoAgentX objects are deliberately contained in this module.  The application only
receives domain contracts through the ``WorkflowEngine`` port.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

import evoagentx

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateReport,
    Capability,
    MissionContract,
    MutableField,
    RunOutcome,
    RunStatus,
    ScoreComponents,
    SystemEdge,
    SystemNode,
)
from evox_api.domain.errors import ImmutablePolicyViolation, IntegrationUnavailable

_PINNED_EVOAGENTX_VERSION = "0.1.4"
_MUTABLE_OPTIMIZER_FIELDS = frozenset({"prompts", "sequential_edges"})


@dataclass(frozen=True)
class SequentialWorkflow:
    """Adapter-local representation of a generated EvoAgentX sequential graph."""

    node_ids: tuple[str, ...]
    prompts: Mapping[str, str]
    models: Mapping[str, str]
    capability_bindings: Mapping[str, frozenset[Capability]]


@dataclass(frozen=True)
class ExecutionResult:
    """Adapter-local receipt from a real workflow execution."""

    output: str
    trace_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    cost_usd: float
    latency_ms: int
    status: RunStatus
    completed_at: datetime | None


@dataclass(frozen=True)
class EvolutionResult:
    """SEW output before the immutable-policy gate is applied."""

    workflow: SequentialWorkflow
    changed_fields: frozenset[str]


class EvoAgentXBackend(Protocol):
    """Private boundary that makes the real SDK replaceable only in isolated tests."""

    async def generate(self, mission: MissionContract) -> SequentialWorkflow: ...

    async def execute(self, system_id: str, input_text: str) -> ExecutionResult: ...

    async def sew(
        self,
        system_id: str,
        current: SequentialWorkflow,
        candidate: CandidateReport,
    ) -> EvolutionResult: ...


class EvoAgentXEngine:
    """Maps the public workflow port to a configured EvoAgentX runtime."""

    def __init__(self, backend: EvoAgentXBackend | None = None) -> None:
        if evoagentx.__version__ != _PINNED_EVOAGENTX_VERSION:
            raise IntegrationUnavailable("evoagentx")
        if backend is None:
            raise IntegrationUnavailable("evoagentx")
        self._backend = backend

    async def forge(self, mission: MissionContract) -> AgenticSystemSpec:
        workflow = await self._backend.generate(mission)
        self._validate_workflow(workflow)
        return self._to_system_spec(mission, workflow)

    async def run(self, system: AgenticSystemSpec, input_text: str) -> RunOutcome:
        receipt = await self._backend.execute(system.id, input_text)
        return RunOutcome(
            id=f"{system.id}-run",
            system_id=system.id,
            output=receipt.output,
            trace_refs=receipt.trace_refs,
            evidence_refs=receipt.evidence_refs,
            score_components=ScoreComponents(
                disposition=0,
                required_facts=0,
                citation_quality=0,
                appropriate_escalation=0,
            ),
            cost_usd=receipt.cost_usd,
            latency_ms=receipt.latency_ms,
            status=receipt.status,
            completed_at=receipt.completed_at,
        )

    async def evolve(
        self, system: AgenticSystemSpec, report: CandidateReport
    ) -> AgenticSystemSpec:
        if report.immutable_policy_digest != system.immutable_policy_digest:
            self._reject_immutable_change(system)
        current = SequentialWorkflow(
            node_ids=tuple(node.id for node in system.nodes),
            prompts=system.prompts,
            models=system.models,
            capability_bindings=system.capability_bindings,
        )
        result = await self._backend.sew(system.id, current, report)
        if result.changed_fields - _MUTABLE_OPTIMIZER_FIELDS:
            self._reject_immutable_change(system)
        self._validate_workflow(result.workflow)
        if (
            result.workflow.models != current.models
            or result.workflow.capability_bindings != current.capability_bindings
            or set(result.workflow.node_ids) != set(current.node_ids)
        ):
            self._reject_immutable_change(system)
        return AgenticSystemSpec(
            id=f"{system.id}-candidate",
            mission_id=system.mission_id,
            version=system.version + 1,
            nodes=tuple(
                SystemNode(id=node_id, kind="evoagentx_step")
                for node_id in result.workflow.node_ids
            ),
            edges=self._sequential_edges(result.workflow.node_ids),
            models=dict(system.models),
            prompts=dict(result.workflow.prompts),
            capability_bindings=dict(system.capability_bindings),
            mutable_fields=system.mutable_fields,
            immutable_policy_digest=system.immutable_policy_digest,
        )

    @staticmethod
    def _validate_workflow(workflow: SequentialWorkflow) -> None:
        if not workflow.node_ids:
            raise IntegrationUnavailable("evoagentx")
        node_ids = set(workflow.node_ids)
        if len(node_ids) != len(workflow.node_ids):
            raise IntegrationUnavailable("evoagentx")
        if set(workflow.prompts) != node_ids or set(workflow.models) != node_ids:
            raise IntegrationUnavailable("evoagentx")
        if set(workflow.capability_bindings) != node_ids:
            raise IntegrationUnavailable("evoagentx")

    @staticmethod
    def _sequential_edges(node_ids: tuple[str, ...]) -> tuple[SystemEdge, ...]:
        return tuple(
            SystemEdge(source=source, target=target)
            for source, target in zip(node_ids, node_ids[1:], strict=False)
        )

    def _to_system_spec(
        self, mission: MissionContract, workflow: SequentialWorkflow
    ) -> AgenticSystemSpec:
        return AgenticSystemSpec(
            id=f"{mission.id}-system",
            mission_id=mission.id,
            version=1,
            nodes=tuple(
                SystemNode(id=node_id, kind="evoagentx_step") for node_id in workflow.node_ids
            ),
            edges=self._sequential_edges(workflow.node_ids),
            models=dict(workflow.models),
            prompts=dict(workflow.prompts),
            capability_bindings=dict(workflow.capability_bindings),
            mutable_fields=frozenset({MutableField.PROMPTS, MutableField.SEQUENTIAL_EDGES}),
            immutable_policy_digest=mission.immutable_policy_digest,
        )

    @staticmethod
    def _reject_immutable_change(system: AgenticSystemSpec) -> None:
        raise ImmutablePolicyViolation(
            expected_digest=system.immutable_policy_digest,
            received_digest=system.immutable_policy_digest,
        )


# The package import deliberately anchors production to the pinned, real
# EvoAgentX distribution. Runtime composition must supply a concrete backend
# configured with a real Pioneer model; there is no production fake or provider
# fallback. EvoAgentX lazily exposes optional workflow submodules, so this module
# does not activate its unrelated tool integrations during API startup.
