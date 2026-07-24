from __future__ import annotations

import json
from typing import Any

from evox_api.domain.contracts import Job
from evox_api.persistence.errors import PersistenceConfigurationError
from evox_api.ports.repositories import QueueBoundary

from .dispatcher import JobDispatcher


class SqsJobQueue(QueueBoundary):
    def __init__(self, client: Any, *, queue_url: str, message_group_id: str = "evox-jobs") -> None:
        if not queue_url:
            raise PersistenceConfigurationError("An SQS job queue URL is required.")
        self._client = client
        self._queue_url = queue_url
        self._message_group_id = message_group_id

    async def enqueue(self, job: Job) -> None:
        message = {
            "QueueUrl": self._queue_url,
            "MessageBody": json.dumps({"job_id": job.id}, separators=(",", ":")),
        }
        if self._queue_url.endswith(".fifo"):
            message["MessageDeduplicationId"] = job.id
            message["MessageGroupId"] = self._message_group_id
        self._client.send_message(**message)


class SqsWorker:
    def __init__(self, client: Any, *, queue_url: str, dispatcher: JobDispatcher) -> None:
        if not queue_url:
            raise PersistenceConfigurationError("An SQS job queue URL is required.")
        self._client = client
        self._queue_url = queue_url
        self._dispatcher = dispatcher

    async def process_once(self) -> int:
        response = self._client.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=20,
        )
        processed = 0
        for message in response.get("Messages", []):
            payload = json.loads(message["Body"])
            await self._dispatcher.dispatch(payload["job_id"])
            self._client.delete_message(
                QueueUrl=self._queue_url,
                ReceiptHandle=message["ReceiptHandle"],
            )
            processed += 1
        return processed
