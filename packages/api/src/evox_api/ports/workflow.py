from typing import Protocol

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateReport,
    MissionContract,
    RunOutcome,
)


class WorkflowEngine(Protocol):
    async def forge(self, mission: MissionContract) -> AgenticSystemSpec: ...

    async def run(self, system: AgenticSystemSpec, input_text: str) -> RunOutcome: ...

    async def evolve(
        self, system: AgenticSystemSpec, report: CandidateReport
    ) -> AgenticSystemSpec: ...
