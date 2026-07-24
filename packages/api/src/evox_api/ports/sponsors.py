from typing import Protocol

from evox_api.domain.contracts import AgenticSystemSpec, RunOutcome


class ModelGateway(Protocol):
    async def generate(self, model: str, prompt: str) -> str: ...


class KnowledgePort(Protocol):
    async def retrieve(self, query: str) -> tuple[str, ...]: ...


class OutcomeMemoryPort(Protocol):
    async def record(self, outcome: RunOutcome) -> None: ...

    async def recall(self, query: str) -> tuple[RunOutcome, ...]: ...


class EscalationPort(Protocol):
    async def escalate(self, run: RunOutcome) -> str: ...


class PublicationPort(Protocol):
    async def publish(self, system: AgenticSystemSpec) -> str: ...

    async def rollback(self, release_id: str) -> None: ...


class QaEvidencePort(Protocol):
    async def capture(self, journey: str) -> str: ...
