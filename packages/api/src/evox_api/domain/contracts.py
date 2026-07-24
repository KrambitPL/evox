from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from pydantic_core import PydanticCustomError

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9_-]{2,127}$")]
MissionId = Identifier
SystemId = Identifier
EvaluationCaseId = Identifier
RunId = Identifier
CandidateId = Identifier
ReleaseId = Identifier
JobId = Identifier


class ContractModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Capability(StrEnum):
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    MODEL_INFERENCE = "model_inference"
    OUTCOME_MEMORY = "outcome_memory"
    HUMAN_ESCALATION = "human_escalation"
    PUBLICATION = "publication"


class EvaluationSplit(StrEnum):
    TRAIN = "train"
    DEV = "dev"
    HELD_OUT = "held_out"


class ResolutionDisposition(StrEnum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    ESCALATE = "escalate"


class RunStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ESCALATED = "escalated"


class ReleaseDisposition(StrEnum):
    PROMOTE = "promote"
    REJECT = "reject"
    OWNER_REVIEW = "owner_review"


class JobType(StrEnum):
    FORGE = "forge"
    RUN = "run"
    EVALUATION = "evaluation"
    EVOLUTION = "evolution"
    PROMOTION = "promotion"
    ROLLBACK = "rollback"


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BudgetPolicy(ContractModel):
    max_cost_usd: Annotated[float, Field(gt=0)]
    max_latency_ms: Annotated[int, Field(gt=0)]
    max_model_calls: Annotated[int, Field(gt=0)]


class EvaluationDatasets(ContractModel):
    train_ref: Annotated[str, Field(min_length=1)]
    dev_ref: Annotated[str, Field(min_length=1)]
    held_out_ref: Annotated[str, Field(min_length=1)]

    @model_validator(mode="after")
    def require_isolated_splits(self) -> EvaluationDatasets:
        references = {self.train_ref, self.dev_ref, self.held_out_ref}
        if len(references) != 3:
            raise ValueError("Evaluation dataset references must be distinct across splits.")
        return self


class HitlPolicy(ContractModel):
    required_for_escalation: bool
    owner_review_required: bool


class ImmutablePolicy(ContractModel):
    allowed_capabilities: frozenset[Capability]
    hard_constraints: tuple[Annotated[str, Field(min_length=1)], ...]
    budgets: BudgetPolicy
    evaluation_datasets: EvaluationDatasets
    hitl_policy: HitlPolicy


class MissionContract(ContractModel):
    id: MissionId
    objective: Annotated[str, Field(min_length=1)]
    success_criteria: tuple[Annotated[str, Field(min_length=1)], ...]
    allowed_capabilities: frozenset[Capability]
    hard_constraints: tuple[Annotated[str, Field(min_length=1)], ...]
    budgets: BudgetPolicy
    evaluation_datasets: EvaluationDatasets
    hitl_policy: HitlPolicy

    @model_validator(mode="after")
    def require_mission_authority(self) -> MissionContract:
        if not self.success_criteria:
            raise ValueError("success_criteria must not be empty.")
        if not self.hard_constraints:
            raise ValueError("hard_constraints must not be empty.")
        return self

    @property
    def immutable_policy(self) -> ImmutablePolicy:
        return ImmutablePolicy(
            allowed_capabilities=self.allowed_capabilities,
            hard_constraints=self.hard_constraints,
            budgets=self.budgets,
            evaluation_datasets=self.evaluation_datasets,
            hitl_policy=self.hitl_policy,
        )

    @property
    def immutable_policy_digest(self) -> str:
        return immutable_policy_digest(self)


class SystemNode(ContractModel):
    id: Identifier
    kind: Annotated[str, Field(min_length=1)]


class SystemEdge(ContractModel):
    source: Identifier
    target: Identifier


class AgenticSystemSpec(ContractModel):
    id: SystemId
    mission_id: MissionId
    version: Annotated[int, Field(ge=1)]
    nodes: tuple[SystemNode, ...]
    edges: tuple[SystemEdge, ...]
    models: dict[Identifier, Annotated[str, Field(min_length=1)]]
    prompts: dict[Identifier, Annotated[str, Field(min_length=1)]]
    capability_bindings: dict[Identifier, frozenset[Capability]]
    mutable_fields: frozenset[Annotated[str, Field(min_length=1)]]
    immutable_policy_digest: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def validate_graph_references(self) -> AgenticSystemSpec:
        node_ids = {node.id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("System node identifiers must be unique.")
        referenced_nodes = {edge.source for edge in self.edges}
        referenced_nodes.update(edge.target for edge in self.edges)
        if unknown_nodes := referenced_nodes - node_ids:
            raise ValueError(f"System edges reference unknown nodes: {sorted(unknown_nodes)}")
        configured_nodes = set(self.models) | set(self.prompts) | set(self.capability_bindings)
        if unknown_nodes := configured_nodes - node_ids:
            raise ValueError(
                f"System configuration references unknown nodes: {sorted(unknown_nodes)}"
            )
        return self

    def validate_against(self, mission: MissionContract) -> None:
        if self.mission_id != mission.id:
            raise ValueError("mission_id does not match the mission contract.")
        expected_digest = immutable_policy_digest(mission)
        if self.immutable_policy_digest != expected_digest:
            raise PydanticCustomError(
                "immutable_policy_digest",
                "immutable_policy_digest does not match the mission policy.",
                {"expected_digest": expected_digest},
            )


class EvaluationCase(ContractModel):
    id: EvaluationCaseId
    mission_id: MissionId
    split: EvaluationSplit
    input: Annotated[str, Field(min_length=1)]
    expected_facts: tuple[Annotated[str, Field(min_length=1)], ...]
    expected_disposition: ResolutionDisposition
    expected_citations: tuple[Annotated[str, Field(min_length=1)], ...]
    hard_gates: tuple[Annotated[str, Field(min_length=1)], ...]


class ScoreComponents(ContractModel):
    disposition: Annotated[float, Field(ge=0, le=1)]
    required_facts: Annotated[float, Field(ge=0, le=1)]
    citation_quality: Annotated[float, Field(ge=0, le=1)]
    appropriate_escalation: Annotated[float, Field(ge=0, le=1)]

    @property
    def overall(self) -> float:
        return round(
            self.disposition * 0.35
            + self.required_facts * 0.35
            + self.citation_quality * 0.20
            + self.appropriate_escalation * 0.10,
            8,
        )


class RunOutcome(ContractModel):
    id: RunId
    system_id: SystemId
    evaluation_case_id: EvaluationCaseId | None = None
    output: str
    trace_refs: tuple[Annotated[str, Field(min_length=1)], ...]
    evidence_refs: tuple[Annotated[str, Field(min_length=1)], ...]
    score_components: ScoreComponents
    cost_usd: Annotated[float, Field(ge=0)]
    latency_ms: Annotated[int, Field(ge=0)]
    status: RunStatus
    completed_at: datetime | None = None

    @property
    def overall_score(self) -> float:
        return self.score_components.overall


class EvaluationMetrics(ContractModel):
    overall_score: Annotated[float, Field(ge=0, le=1)]
    disposition_score: Annotated[float, Field(default=0, ge=0, le=1)] = 0
    required_facts_score: Annotated[float, Field(default=0, ge=0, le=1)] = 0
    citation_quality_score: Annotated[float, Field(default=0, ge=0, le=1)] = 0
    appropriate_escalation_score: Annotated[float, Field(default=0, ge=0, le=1)] = 0


class CandidateDiff(ContractModel):
    field: Annotated[str, Field(min_length=1)]
    before: Any
    after: Any


class CandidateReport(ContractModel):
    id: CandidateId
    mission_id: MissionId
    baseline_system_id: SystemId
    candidate_system_id: SystemId
    baseline_metrics: EvaluationMetrics
    candidate_metrics: EvaluationMetrics
    repeated_results: tuple[tuple[EvaluationCaseId, tuple[float, ...]], ...]
    diffs: tuple[CandidateDiff, ...]
    invariant_results: dict[Annotated[str, Field(min_length=1)], bool]
    immutable_policy_digest: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]

    @property
    def improvement(self) -> float:
        return round(self.candidate_metrics.overall_score - self.baseline_metrics.overall_score, 8)


class ReleaseDecision(ContractModel):
    id: ReleaseId
    candidate_id: CandidateId
    disposition: ReleaseDisposition
    reasons: tuple[Annotated[str, Field(min_length=1)], ...]
    evidence_refs: tuple[Annotated[str, Field(min_length=1)], ...]
    promoted_version: str | None = None
    rollback_version: str | None = None
    immutable_policy_digest: Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]

    @model_validator(mode="after")
    def require_promotion_receipt(self) -> ReleaseDecision:
        if self.disposition is ReleaseDisposition.PROMOTE and (
            not self.evidence_refs or not self.promoted_version or not self.rollback_version
        ):
            raise ValueError("Promotion requires evidence, promoted_version, and rollback_version.")
        return self


class Job(ContractModel):
    id: JobId
    type: JobType
    status: JobStatus
    created_at: datetime
    updated_at: datetime
    result_ref: str | None
    failure: str | None

    @model_validator(mode="after")
    def validate_terminal_result(self) -> Job:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at.")
        if self.status is JobStatus.SUCCEEDED and not self.result_ref:
            raise ValueError("A succeeded job requires result_ref.")
        if self.status is JobStatus.FAILED and not self.failure:
            raise ValueError("A failed job requires failure.")
        return self


def immutable_policy_digest(mission: MissionContract) -> str:
    canonical_policy = _canonicalize(mission.immutable_policy.model_dump(mode="python"))
    payload = json.dumps(canonical_policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return sha256(payload.encode("utf-8")).hexdigest()


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(item) for key, item in sorted(value.items())}
    if isinstance(value, (frozenset, set, tuple, list)):
        values = [_canonicalize(item) for item in value]
        if isinstance(value, (frozenset, set)):
            return sorted(values, key=lambda item: json.dumps(item, sort_keys=True))
        return values
    if isinstance(value, StrEnum):
        return value.value
    return value
