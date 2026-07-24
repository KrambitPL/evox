from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NoReturn
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from evox_api.domain.contracts import (
    CandidateReport,
    Job,
    JobStatus,
    JobType,
    MissionContract,
    RunOutcome,
)
from evox_api.domain.errors import DomainError, ImmutablePolicyViolation, IntegrationUnavailable
from evox_api.integrations import integration_health
from evox_api.jobs.queue import SqsJobQueue
from evox_api.persistence import (
    AwsPersistence,
    DynamoCandidateRepository,
    DynamoJobRepository,
    DynamoMissionRepository,
)
from evox_api.persistence.errors import PersistenceConfigurationError
from evox_api.ports.repositories import (
    CandidateRepository,
    JobRepository,
    MissionRepository,
    QueueBoundary,
)

IntegrationHealth = Callable[[], Awaitable[dict[str, Any]]]


@dataclass(frozen=True, slots=True)
class ApplicationRuntime:
    missions: MissionRepository
    jobs: JobRepository
    candidates: CandidateRepository
    queue: QueueBoundary
    integration_health: IntegrationHealth


def build_runtime() -> ApplicationRuntime:
    aws = AwsPersistence.from_environment()
    return ApplicationRuntime(
        missions=DynamoMissionRepository(aws.dynamodb_table),
        jobs=DynamoJobRepository(aws.dynamodb_table),
        candidates=DynamoCandidateRepository(aws.dynamodb_table),
        queue=SqsJobQueue(aws.sqs_client, queue_url=aws.settings.jobs_queue_url),
        integration_health=integration_health,
    )


def create_app(runtime: ApplicationRuntime | None = None) -> FastAPI:
    app = FastAPI(title="Evox API", version="0.1.0")
    app.add_exception_handler(DomainError, domain_error_response)
    configured_runtime = runtime

    def require_runtime() -> ApplicationRuntime:
        nonlocal configured_runtime
        if configured_runtime is None:
            try:
                configured_runtime = build_runtime()
            except PersistenceConfigurationError:
                unavailable("persistence")
        return configured_runtime

    async def enqueue(job_type: JobType) -> Job:
        now = datetime.now(tz=UTC)
        job = Job(
            id=f"job-{uuid4().hex}",
            type=job_type,
            status=JobStatus.QUEUED,
            created_at=now,
            updated_at=now,
            result_ref=None,
            failure=None,
        )
        services = require_runtime()
        await services.jobs.save(job)
        await services.queue.enqueue(job)
        return job

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ready"}

    @app.post("/v1/missions", response_model=MissionContract, status_code=status.HTTP_201_CREATED)
    async def create_mission(mission: MissionContract) -> MissionContract:
        await require_runtime().missions.save(mission)
        return mission

    @app.get("/v1/missions/{id}", response_model=MissionContract)
    async def get_mission(id: str) -> MissionContract:
        mission = await require_runtime().missions.get(id)
        if mission is None:
            raise HTTPException(status_code=404, detail="Mission not found.")
        return mission

    @app.post("/v1/missions/{id}/forge", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
    async def forge_mission(id: str) -> Job:
        if await require_runtime().missions.get(id) is None:
            raise HTTPException(status_code=404, detail="Mission not found.")
        return await enqueue(JobType.FORGE)

    @app.post("/v1/systems/{id}/runs", response_model=Job, status_code=status.HTTP_202_ACCEPTED)
    async def run_system(id: str, input_text: str) -> Job:
        del id, input_text
        return await enqueue(JobType.RUN)

    @app.post(
        "/v1/systems/{id}/evaluations", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def evaluate_system(id: str) -> Job:
        del id
        return await enqueue(JobType.EVALUATION)

    @app.post(
        "/v1/systems/{id}/evolutions", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def evolve_system(id: str) -> Job:
        del id
        return await enqueue(JobType.EVOLUTION)

    @app.get("/v1/jobs/{id}", response_model=Job)
    async def get_job(id: str) -> Job:
        job = await require_runtime().jobs.get(id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found.")
        return job

    @app.get("/v1/candidates/{id}", response_model=CandidateReport)
    async def get_candidate(id: str) -> CandidateReport:
        candidate = await require_runtime().candidates.get(id)
        if candidate is None:
            raise HTTPException(status_code=404, detail="Candidate not found.")
        return candidate

    @app.post(
        "/v1/candidates/{id}/promote", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def promote_candidate(id: str) -> Job:
        del id
        return await enqueue(JobType.PROMOTION)

    @app.post(
        "/v1/releases/{id}/rollback", response_model=Job, status_code=status.HTTP_202_ACCEPTED
    )
    async def rollback_release(id: str) -> Job:
        del id
        return await enqueue(JobType.ROLLBACK)

    @app.post("/v1/runs/{id}/feedback", response_model=RunOutcome)
    async def submit_feedback(id: str, feedback: str) -> RunOutcome:
        del id, feedback
        unavailable("outcome persistence")

    @app.get("/v1/integrations/health", response_model=dict[str, Any])
    async def integrations_health() -> dict[str, Any]:
        try:
            services = require_runtime()
        except IntegrationUnavailable as error:
            raise DomainError(
                code="integration_unavailable",
                message="Integration health checks are not configured.",
                details={"integration": "health"},
            ) from error
        return await services.integration_health()

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
