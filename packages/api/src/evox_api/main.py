from typing import NoReturn

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from evox_api.domain.contracts import (
    CandidateReport,
    Job,
    MissionContract,
    RunOutcome,
)
from evox_api.domain.errors import DomainError, ImmutablePolicyViolation, IntegrationUnavailable


def create_app() -> FastAPI:
    app = FastAPI(title="Evox API", version="0.1.0")
    app.add_exception_handler(DomainError, domain_error_response)

    @app.post("/v1/missions", response_model=MissionContract, status_code=status.HTTP_201_CREATED)
    async def create_mission(mission: MissionContract) -> MissionContract:
        del mission
        unavailable("persistence")

    @app.get("/v1/missions/{id}", response_model=MissionContract)
    async def get_mission(id: str) -> MissionContract:
        del id
        unavailable("persistence")

    @app.post("/v1/missions/{id}/forge", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
    async def forge_mission(id: str) -> Job:
        del id
        unavailable("queue")

    @app.post("/v1/systems/{id}/runs", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
    async def run_system(id: str, input_text: str) -> Job:
        del id, input_text
        unavailable("queue")

    @app.post(
        "/v1/systems/{id}/evaluations", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def evaluate_system(id: str) -> Job:
        del id
        unavailable("queue")

    @app.post(
        "/v1/systems/{id}/evolutions", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def evolve_system(id: str) -> Job:
        del id
        unavailable("queue")

    @app.get("/v1/jobs/{id}", response_model=Job)
    async def get_job(id: str) -> Job:
        del id
        unavailable("persistence")

    @app.get("/v1/candidates/{id}", response_model=CandidateReport)
    async def get_candidate(id: str) -> CandidateReport:
        del id
        unavailable("persistence")

    @app.post(
        "/v1/candidates/{id}/promote", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def promote_candidate(id: str) -> Job:
        del id
        unavailable("queue")

    @app.post(
        "/v1/releases/{id}/rollback", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def rollback_release(id: str) -> Job:
        del id
        unavailable("queue")

    @app.post("/v1/runs/{id}/feedback", response_model=RunOutcome)
    async def submit_feedback(id: str, feedback: str) -> RunOutcome:
        del id, feedback
        unavailable("persistence")

    @app.get("/v1/integrations/health", response_model=dict[str, str])
    async def integration_health() -> dict[str, str]:
        raise DomainError(
            code="integration_unavailable",
            message="Integration health checks are not configured.",
            details={"integration": "health"},
        )

    return app


async def domain_error_response(_: Request, error: DomainError) -> JSONResponse:
    response_status = (
        status.HTTP_409_CONFLICT
        if isinstance(error, ImmutablePolicyViolation)
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(
        status_code=response_status,
        content=error.payload().model_dump(mode="json"),
    )


def unavailable(integration: str) -> NoReturn:
    raise IntegrationUnavailable(integration)


app = create_app()
