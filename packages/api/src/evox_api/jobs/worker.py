from __future__ import annotations

import asyncio

from evox_api.persistence import AwsPersistence, DynamoJobRepository

from .dispatcher import JobDispatcher
from .queue import SqsWorker


async def run_worker() -> None:
    aws = AwsPersistence.from_environment()
    jobs = DynamoJobRepository(aws.dynamodb_table)
    dispatcher = JobDispatcher(jobs, {})
    worker = SqsWorker(
        aws.sqs_client,
        queue_url=aws.settings.jobs_queue_url,
        dispatcher=dispatcher,
    )
    while True:
        await worker.process_once()


def main() -> None:
    asyncio.run(run_worker())
