from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from datetime import UTC, datetime

from evox_api.domain.contracts import Job, JobStatus, JobType
from evox_api.persistence.aws import DynamoJobRepository
from evox_api.persistence.errors import ConcurrencyConflict

JobHandler = Callable[[Job], Awaitable[str]]


class JobDispatcher:
    def __init__(
        self, repository: DynamoJobRepository, handlers: Mapping[JobType, JobHandler]
    ) -> None:
        self._repository = repository
        self._handlers = dict(handlers)

    async def dispatch(self, job_id: str) -> Job:
        queued = await self._repository.get(job_id)
        if queued is None:
            raise LookupError(f"Job {job_id} does not exist.")
        running = queued.model_copy(update={"status": JobStatus.RUNNING, "updated_at": _now()})
        await self._repository.compare_and_set(running, expected_status=JobStatus.QUEUED)
        handler = self._handlers.get(running.type)
        if handler is None:
            return await self._fail(
                running, f"No configured handler for job type {running.type.value}."
            )
        try:
            result_ref = await handler(running)
        except Exception as error:
            return await self._fail(running, f"Job execution failed: {error}")
        completed = running.model_copy(
            update={"status": JobStatus.SUCCEEDED, "result_ref": result_ref, "updated_at": _now()}
        )
        await self._repository.compare_and_set(completed, expected_status=JobStatus.RUNNING)
        return completed

    async def _fail(self, running: Job, failure: str) -> Job:
        failed = running.model_copy(
            update={"status": JobStatus.FAILED, "failure": failure, "updated_at": _now()}
        )
        try:
            await self._repository.compare_and_set(failed, expected_status=JobStatus.RUNNING)
        except ConcurrencyConflict:
            raise
        return failed


def _now() -> datetime:
    return datetime.now(tz=UTC)
