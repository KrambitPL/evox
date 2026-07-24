from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from evox_api.domain.contracts import AgenticSystemSpec, ReleaseDecision, RunOutcome


@dataclass(frozen=True)
class KnowledgeCitation:
    source_uri: str
    source_title: str
    retrieved_at: datetime
    tenant_id: str


@dataclass(frozen=True)
class KnowledgeResult:
    content: str
    citations: tuple[KnowledgeCitation, ...]


class ModelGateway(Protocol):
    async def generate(self, model: str, prompt: str) -> str: ...


class KnowledgePort(Protocol):
    async def retrieve(
        self, query: str, *, tenant_id: str, filters: Mapping[str, str]
    ) -> tuple[KnowledgeResult, ...]: ...


class OutcomeMemoryPort(Protocol):
    async def record(self, outcome: RunOutcome, *, tenant_id: str) -> None: ...

    async def recall(
        self, query: str, *, tenant_id: str, filters: Mapping[str, str]
    ) -> tuple[RunOutcome, ...]: ...


class EscalationPort(Protocol):
    async def escalate(self, run: RunOutcome) -> str: ...


class PublicationPort(Protocol):
    async def publish(self, release: ReleaseDecision, system: AgenticSystemSpec) -> str: ...

    async def rollback(self, release_id: str) -> None: ...


class QaEvidencePort(Protocol):
    async def capture(self, journey: str) -> str: ...
