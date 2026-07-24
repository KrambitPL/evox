from typing import Protocol

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateId,
    CandidateReport,
    EvaluationCase,
    Job,
    JobId,
    MissionContract,
    MissionId,
    ReleaseDecision,
    RunOutcome,
    SystemId,
)


class MissionRepository(Protocol):
    async def get(self, mission_id: MissionId) -> MissionContract | None: ...

    async def save(self, mission: MissionContract) -> None: ...


class SystemRepository(Protocol):
    async def get(self, system_id: SystemId) -> AgenticSystemSpec | None: ...

    async def save(self, system: AgenticSystemSpec) -> None: ...


class EvaluationRepository(Protocol):
    async def list_for_mission(self, mission_id: MissionId) -> tuple[EvaluationCase, ...]: ...


class OutcomeRepository(Protocol):
    async def save(self, outcome: RunOutcome) -> None: ...


class CandidateRepository(Protocol):
    async def get(self, candidate_id: CandidateId) -> CandidateReport | None: ...

    async def save(self, report: CandidateReport) -> None: ...


class ReleaseRepository(Protocol):
    async def save(self, decision: ReleaseDecision) -> None: ...


class JobRepository(Protocol):
    async def get(self, job_id: JobId) -> Job | None: ...

    async def save(self, job: Job) -> None: ...


class QueueBoundary(Protocol):
    async def enqueue(self, job: Job) -> None: ...
