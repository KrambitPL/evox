from __future__ import annotations

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import boto3
from pydantic import BaseModel

from evox_api.domain.contracts import (
    AgenticSystemSpec,
    CandidateReport,
    EvaluationCase,
    Job,
    JobStatus,
    MissionContract,
    ReleaseDecision,
    RunOutcome,
)

from .errors import ConcurrencyConflict, PersistenceConfigurationError

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass(frozen=True, slots=True)
class AwsSettings:
    region: str
    dynamodb_table: str
    evidence_bucket: str
    jobs_queue_url: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> AwsSettings:
        source = os.environ if environment is None else environment
        values = {
            "EVOX_AWS_REGION": source.get("EVOX_AWS_REGION", ""),
            "EVOX_DYNAMODB_TABLE": source.get("EVOX_DYNAMODB_TABLE", ""),
            "EVOX_EVIDENCE_BUCKET": source.get("EVOX_EVIDENCE_BUCKET", ""),
            "EVOX_JOBS_QUEUE_URL": source.get("EVOX_JOBS_QUEUE_URL", ""),
        }
        missing = [name for name, value in values.items() if not value.strip()]
        if missing:
            raise PersistenceConfigurationError(
                f"Missing required AWS configuration: {', '.join(missing)}"
            )
        return cls(
            region=values["EVOX_AWS_REGION"],
            dynamodb_table=values["EVOX_DYNAMODB_TABLE"],
            evidence_bucket=values["EVOX_EVIDENCE_BUCKET"],
            jobs_queue_url=values["EVOX_JOBS_QUEUE_URL"],
        )


@dataclass(frozen=True, slots=True)
class AwsPersistence:
    settings: AwsSettings
    dynamodb_table: Any
    s3_client: Any
    sqs_client: Any

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> AwsPersistence:
        settings = AwsSettings.from_environment(environment)
        session = boto3.Session(region_name=settings.region)
        credentials = session.get_credentials()
        if credentials is None:
            raise PersistenceConfigurationError("AWS credentials are unavailable.")
        return cls(
            settings=settings,
            dynamodb_table=session.resource("dynamodb").Table(settings.dynamodb_table),
            s3_client=session.client("s3"),
            sqs_client=session.client("sqs"),
        )


class DynamoModelRepository(Generic[ModelT]):
    def __init__(self, table: Any, *, entity_type: str, model_type: type[ModelT]) -> None:
        self._table = table
        self._entity_type = entity_type
        self._model_type = model_type

    def _key(self, identifier: str) -> dict[str, str]:
        return {"pk": f"{self._entity_type}#{identifier}", "sk": self._entity_type}

    async def get(self, identifier: str) -> ModelT | None:
        response = self._table.get_item(Key=self._key(identifier), ConsistentRead=True)
        item = response.get("Item")
        if item is None:
            return None
        return self._model_type.model_validate_json(item["payload"])

    async def save(self, model: ModelT) -> None:
        identifier = str(model.id)
        item = {
            **self._key(identifier),
            "payload": model.model_dump_json(),
            "entity_type": self._entity_type,
        }
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
        except Exception as error:
            if _is_conditional_failure(error):
                raise ConcurrencyConflict(
                    f"{self._entity_type} {identifier} already exists or changed."
                ) from error
            raise


class DynamoMissionRepository(DynamoModelRepository[MissionContract]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="mission", model_type=MissionContract)


class DynamoSystemRepository(DynamoModelRepository[AgenticSystemSpec]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="system", model_type=AgenticSystemSpec)


class DynamoCandidateRepository(DynamoModelRepository[CandidateReport]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="candidate", model_type=CandidateReport)


class DynamoReleaseRepository(DynamoModelRepository[ReleaseDecision]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="release", model_type=ReleaseDecision)


class DynamoOutcomeRepository(DynamoModelRepository[RunOutcome]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="outcome", model_type=RunOutcome)


class DynamoEvaluationRepository:
    def __init__(self, table: Any) -> None:
        self._table = table

    async def list_for_mission(self, mission_id: str) -> tuple[EvaluationCase, ...]:
        response = self._table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"evaluation#{mission_id}"},
            ConsistentRead=True,
        )
        return tuple(
            EvaluationCase.model_validate_json(item["payload"])
            for item in response.get("Items", [])
        )


class DynamoJobRepository(DynamoModelRepository[Job]):
    def __init__(self, table: Any) -> None:
        super().__init__(table, entity_type="job", model_type=Job)

    async def save(self, job: Job) -> None:
        item = {
            **self._key(job.id),
            "payload": job.model_dump_json(),
            "status": job.status.value,
            "idempotency_key": job.id,
            "entity_type": "job",
        }
        try:
            self._table.put_item(Item=item, ConditionExpression="attribute_not_exists(pk)")
        except Exception as error:
            if _is_conditional_failure(error):
                raise ConcurrencyConflict(f"Job {job.id} was already created.") from error
            raise

    async def compare_and_set(self, job: Job, *, expected_status: JobStatus) -> None:
        try:
            self._table.update_item(
                Key=self._key(job.id),
                UpdateExpression="SET payload = :payload, #status = :status",
                ConditionExpression="#status = :expected",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":payload": job.model_dump_json(),
                    ":status": job.status.value,
                    ":expected": expected_status.value,
                },
            )
        except Exception as error:
            if _is_conditional_failure(error):
                raise ConcurrencyConflict(
                    f"Job {job.id} was not {expected_status.value} when claimed."
                ) from error
            raise


class S3ArtifactStore:
    def __init__(self, client: Any, *, bucket: str) -> None:
        if not bucket:
            raise PersistenceConfigurationError("An evidence bucket is required.")
        self._client = client
        self._bucket = bucket

    async def put_json(self, key: str, document: Mapping[str, Any]) -> str:
        if not key or key.startswith("/") or ".." in key.split("/"):
            raise ValueError("Artifact keys must be non-empty relative paths.")
        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            ContentType="application/json",
            ServerSideEncryption="aws:kms",
        )
        return f"s3://{self._bucket}/{key}"

    async def get_json(self, reference: str) -> dict[str, Any]:
        prefix = f"s3://{self._bucket}/"
        if not reference.startswith(prefix):
            raise ValueError("Artifact reference is outside the configured evidence bucket.")
        response = self._client.get_object(Bucket=self._bucket, Key=reference.removeprefix(prefix))
        return json.loads(response["Body"].read())


def _is_conditional_failure(error: Exception) -> bool:
    if getattr(error, "code", None) == "ConditionalCheckFailedException":
        return True
    response = getattr(error, "response", {})
    return response.get("Error", {}).get("Code") == "ConditionalCheckFailedException"
