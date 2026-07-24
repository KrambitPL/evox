import asyncio
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from evox_api.adapters.band.escalation import (
    BandEscalationPort,
    BandResponseProcessor,
    EscalationConfig,
    EscalationExpired,
    JobQueueEscalationResumer,
    SqliteEscalationStore,
)
from evox_api.domain.contracts import (
    Job,
    JobStatus,
    JobType,
    RunOutcome,
    RunStatus,
    ScoreComponents,
)


class FakeBandRooms:
    def __init__(self) -> None:
        self.created: list[tuple[str, str]] = []
        self.participants: list[tuple[str, str]] = []
        self.messages: list[tuple[str, str, str]] = []

    async def create_room(self, *, title: str) -> str:
        self.created.append((title, "room-123"))
        return "room-123"

    async def add_participant(self, *, room_id: str, participant_id: str) -> None:
        self.participants.append((room_id, participant_id))

    async def send_message(
        self, *, room_id: str, content: str, mention_id: str, mention_handle: str
    ) -> None:
        self.messages.append((room_id, content, mention_id))


class FakeResumer:
    def __init__(self) -> None:
        self.resumed: list[tuple[str, str, str, str, str]] = []
        self.expired: list[tuple[str, str, str]] = []

    async def resume(
        self, *, job_id: str, run_id: str, correlation_id: str, decision: str, response: str
    ) -> None:
        self.resumed.append((job_id, run_id, correlation_id, decision, response))

    async def expire(self, *, job_id: str, run_id: str, correlation_id: str) -> None:
        self.expired.append((job_id, run_id, correlation_id))


def _run() -> RunOutcome:
    return RunOutcome(
        id="run-123",
        system_id="system-123",
        output="Unable to satisfy an immutable constraint.",
        trace_refs=("trace://run-123",),
        evidence_refs=("evidence://run-123",),
        score_components=ScoreComponents(
            disposition=1,
            required_facts=1,
            citation_quality=1,
            appropriate_escalation=1,
        ),
        cost_usd=0,
        latency_ms=1,
        status=RunStatus.ESCALATED,
    )


def _config() -> EscalationConfig:
    return EscalationConfig(
        agent_id="agent-123",
        api_key="secret",
        human_id="human-123",
        human_handle="owner",
        response_ttl=timedelta(minutes=5),
    )


def test_escalation_creates_one_correlated_band_room_and_is_idempotent(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = SqliteEscalationStore(tmp_path / "escalations.sqlite3")
        rooms = FakeBandRooms()
        port = BandEscalationPort(config=_config(), store=store, rooms=rooms)

        first = await port.escalate(_run(), job_id="job-123")
        second = await port.escalate(_run(), job_id="job-123")

        assert first == second == "escalation-run-123"
        assert rooms.created == [("Evox escalation escalation-run-123", "room-123")]
        assert rooms.participants == [("room-123", "human-123")]
        assert "correlation_id=escalation-run-123" in rooms.messages[0][1]

    asyncio.run(exercise())


def test_correlated_human_response_resumes_once_and_rejects_another_identity(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        store = SqliteEscalationStore(tmp_path / "escalations.sqlite3")
        rooms = FakeBandRooms()
        resumer = FakeResumer()
        port = BandEscalationPort(config=_config(), store=store, rooms=rooms)
        await port.escalate(_run(), job_id="job-123")
        processor = BandResponseProcessor(config=_config(), store=store, resumer=resumer)
        payload = json.dumps(
            {
                "correlation_id": "escalation-run-123",
                "decision": "approve",
                "reason": "The exception is approved.",
                "responded_at": "2026-07-24T12:00:00Z",
            }
        )

        assert not await processor.process(
            message_id="message-wrong-person",
            room_id="room-123",
            sender_id="human-other",
            sender_type="user",
            content=payload,
        )
        assert await processor.process(
            message_id="message-123",
            room_id="room-123",
            sender_id="human-123",
            sender_type="user",
            content=payload,
        )
        assert await processor.process(
            message_id="message-123",
            room_id="room-123",
            sender_id="human-123",
            sender_type="user",
            content=payload,
        )
        assert resumer.resumed == [
            (
                "job-123",
                "run-123",
                "escalation-run-123",
                "approve",
                "The exception is approved.",
            )
        ]

    asyncio.run(exercise())


def test_expired_response_fails_closed_and_expires_the_waiting_job(tmp_path: Path) -> None:
    async def exercise() -> None:
        store = SqliteEscalationStore(tmp_path / "escalations.sqlite3")
        rooms = FakeBandRooms()
        resumer = FakeResumer()
        config = replace(_config(), response_ttl=timedelta(seconds=-1))
        await BandEscalationPort(config=config, store=store, rooms=rooms).escalate(
            _run(), job_id="job-123"
        )
        processor = BandResponseProcessor(config=config, store=store, resumer=resumer)

        with pytest.raises(EscalationExpired):
            await processor.process(
                message_id="message-123",
                room_id="room-123",
                sender_id="human-123",
                sender_type="user",
                content=json.dumps(
                    {
                        "correlation_id": "escalation-run-123",
                        "decision": "reject",
                        "reason": "Too late.",
                        "responded_at": datetime.now(UTC).isoformat(),
                    }
                ),
            )
        assert resumer.expired == [("job-123", "run-123", "escalation-run-123")]

    asyncio.run(exercise())


def test_job_queue_resumer_requeues_approval_and_fails_expiry() -> None:
    class Jobs:
        def __init__(self) -> None:
            self.job = Job(
                id="job-123",
                type=JobType.RUN,
                status=JobStatus.RUNNING,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
                result_ref=None,
                failure=None,
            )

        async def get(self, job_id: str) -> Job | None:
            return self.job if job_id == self.job.id else None

        async def save(self, job: Job) -> None:
            self.job = job

    class Queue:
        def __init__(self) -> None:
            self.jobs: list[Job] = []

        async def enqueue(self, job: Job) -> None:
            self.jobs.append(job)

    async def exercise() -> None:
        jobs = Jobs()
        queue = Queue()
        resumer = JobQueueEscalationResumer(jobs=jobs, queue=queue)
        await resumer.resume(
            job_id="job-123",
            run_id="run-123",
            correlation_id="escalation-run-123",
            decision="approve",
            response="Approved by owner.",
        )
        assert jobs.job.status is JobStatus.QUEUED
        assert queue.jobs == [jobs.job]
        await resumer.expire(
            job_id="job-123", run_id="run-123", correlation_id="escalation-run-123"
        )
        assert jobs.job.status is JobStatus.FAILED
        assert jobs.job.failure == "Band escalation expired without a valid human response."

    asyncio.run(exercise())
