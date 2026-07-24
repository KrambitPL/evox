from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

import pytest

from evox_api.domain.contracts import Job, JobStatus, JobType
from evox_api.jobs.dispatcher import JobDispatcher
from evox_api.jobs.queue import SqsJobQueue
from evox_api.persistence.aws import AwsSettings, DynamoJobRepository, S3ArtifactStore
from evox_api.persistence.errors import ConcurrencyConflict, PersistenceConfigurationError


def job(
    status: JobStatus = JobStatus.QUEUED,
    *,
    result_ref: str | None = None,
    failure: str | None = None,
) -> Job:
    now = datetime(2026, 7, 24, tzinfo=UTC)
    return Job(
        id="job-persistence-001",
        type=JobType.FORGE,
        status=status,
        created_at=now,
        updated_at=now,
        result_ref=result_ref,
        failure=failure,
    )


class FakeDynamoTable:
    def __init__(self) -> None:
        self.items: dict[tuple[str, str], dict[str, Any]] = {}

    def put_item(self, **kwargs: Any) -> None:
        item = kwargs["Item"]
        key = (item["pk"], item["sk"])
        if kwargs.get("ConditionExpression") == "attribute_not_exists(pk)" and key in self.items:
            raise FakeConditionalCheckFailed()
        self.items[key] = item

    def get_item(self, **kwargs: Any) -> dict[str, Any]:
        key = (kwargs["Key"]["pk"], kwargs["Key"]["sk"])
        item = self.items.get(key)
        return {"Item": item} if item else {}

    def update_item(self, **kwargs: Any) -> None:
        key = (kwargs["Key"]["pk"], kwargs["Key"]["sk"])
        item = self.items[key]
        expected = kwargs["ExpressionAttributeValues"][":expected"]
        if item["status"] != expected:
            raise FakeConditionalCheckFailed()
        item["payload"] = kwargs["ExpressionAttributeValues"][":payload"]
        item["status"] = kwargs["ExpressionAttributeValues"][":status"]


class FakeConditionalCheckFailed(Exception):
    code = "ConditionalCheckFailedException"


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **kwargs: Any) -> None:
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        return {"Body": FakeBody(self.objects[(kwargs["Bucket"], kwargs["Key"])])}


class FakeBody:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return self.payload


class FakeSqsClient:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def send_message(self, **kwargs: Any) -> None:
        self.messages.append(kwargs)


def test_aws_settings_fail_closed_when_required_configuration_is_missing() -> None:
    with pytest.raises(PersistenceConfigurationError, match="EVOX_AWS_REGION"):
        AwsSettings.from_environment({})


def test_job_repository_enforces_create_idempotency_and_status_concurrency() -> None:
    async def scenario() -> None:
        repository = DynamoJobRepository(FakeDynamoTable())
        queued = job()
        await repository.save(queued)
        assert await repository.get(queued.id) == queued

        with pytest.raises(ConcurrencyConflict):
            await repository.save(queued)

        running = job(JobStatus.RUNNING)
        await repository.compare_and_set(running, expected_status=JobStatus.QUEUED)
        assert await repository.get(queued.id) == running

        with pytest.raises(ConcurrencyConflict):
            await repository.compare_and_set(running, expected_status=JobStatus.QUEUED)

    asyncio.run(scenario())


def test_s3_artifact_store_round_trips_json_with_immutable_reference() -> None:
    async def scenario() -> None:
        store = S3ArtifactStore(FakeS3Client(), bucket="evox-evidence")
        reference = await store.put_json("runs/job-persistence-001.json", {"score": 0.9})
        assert reference == "s3://evox-evidence/runs/job-persistence-001.json"
        assert await store.get_json(reference) == {"score": 0.9}

    asyncio.run(scenario())


def test_sqs_queue_uses_job_id_as_idempotency_key() -> None:
    async def scenario() -> None:
        client = FakeSqsClient()
        queue = SqsJobQueue(client, queue_url="https://sqs.example/jobs.fifo")
        await queue.enqueue(job())
        assert client.messages == [
            {
                "QueueUrl": "https://sqs.example/jobs.fifo",
                "MessageBody": '{"job_id":"job-persistence-001"}',
                "MessageDeduplicationId": "job-persistence-001",
                "MessageGroupId": "evox-jobs",
            }
        ]

    asyncio.run(scenario())


def test_dispatcher_records_explicit_failure_after_claiming_job() -> None:
    async def failing_handler(_: Job) -> str:
        raise RuntimeError("provider unavailable")

    async def scenario() -> None:
        repository = DynamoJobRepository(FakeDynamoTable())
        queued = job()
        await repository.save(queued)
        dispatcher = JobDispatcher(repository, {JobType.FORGE: failing_handler})

        completed = await dispatcher.dispatch(queued.id)

        assert completed.status is JobStatus.FAILED
        assert completed.failure == "Job execution failed: provider unavailable"
        assert await repository.get(queued.id) == completed

    asyncio.run(scenario())
