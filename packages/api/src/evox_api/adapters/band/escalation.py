"""Durable, fail-closed human escalation through Band."""

from __future__ import annotations

import asyncio
import os
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from band import Agent
from band.client.rest import (
    DEFAULT_REQUEST_OPTIONS,
    AsyncRestClient,
    ChatMessageRequest,
    ChatMessageRequestMentionsItem,
    ChatRoomRequest,
    ParticipantRequest,
)
from band.core.simple_adapter import SimpleAdapter
from band.core.types import HistoryProvider, PlatformMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evox_api.domain.contracts import JobStatus, RunOutcome
from evox_api.domain.errors import IntegrationUnavailable
from evox_api.ports.repositories import JobRepository, QueueBoundary


class EscalationError(RuntimeError):
    """A Band escalation could not be safely completed."""


class EscalationExpired(EscalationError):
    """The human responded after the approved escalation window."""


class HumanDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class HumanResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    correlation_id: str = Field(pattern=r"^escalation-[a-z][a-z0-9_-]{2,127}$")
    decision: HumanDecision
    reason: str = Field(min_length=1, max_length=4_000)
    responded_at: datetime


@dataclass(frozen=True)
class EscalationConfig:
    agent_id: str
    api_key: str
    human_id: str
    human_handle: str
    response_ttl: timedelta = timedelta(hours=24)
    rest_url: str = "https://app.band.ai"
    ws_url: str = "wss://app.band.ai/api/v1/socket/websocket"

    @classmethod
    def from_environment(cls) -> EscalationConfig:
        values = {
            "agent_id": os.getenv("EVOX_BAND_AGENT_ID"),
            "api_key": os.getenv("EVOX_BAND_API_KEY"),
            "human_id": os.getenv("EVOX_BAND_HUMAN_ID"),
            "human_handle": os.getenv("EVOX_BAND_HUMAN_HANDLE"),
        }
        if any(not value for value in values.values()):
            raise IntegrationUnavailable("band")
        return cls(
            agent_id=values["agent_id"] or "",
            api_key=values["api_key"] or "",
            human_id=values["human_id"] or "",
            human_handle=values["human_handle"] or "",
            rest_url=os.getenv("EVOX_BAND_REST_URL", "https://app.band.ai"),
            ws_url=os.getenv(
                "EVOX_BAND_WS_URL", "wss://app.band.ai/api/v1/socket/websocket"
            ),
        )


class BandRooms(Protocol):
    async def create_room(self, *, title: str) -> str: ...

    async def add_participant(self, *, room_id: str, participant_id: str) -> None: ...

    async def send_message(
        self, *, room_id: str, content: str, mention_id: str, mention_handle: str
    ) -> None: ...


class BandSdkRooms:
    """Small production-only facade over the official Band REST client."""

    def __init__(self, config: EscalationConfig) -> None:
        self._client = AsyncRestClient(base_url=config.rest_url, api_key=config.api_key)

    async def create_room(self, *, title: str) -> str:
        response = await self._client.agent_api_chats.create_agent_chat(
            chat=ChatRoomRequest(title=title), request_options=DEFAULT_REQUEST_OPTIONS
        )
        return response.data.id

    async def add_participant(self, *, room_id: str, participant_id: str) -> None:
        await self._client.agent_api_participants.add_agent_chat_participant(
            room_id,
            participant=ParticipantRequest(participant_id=participant_id),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )

    async def send_message(
        self, *, room_id: str, content: str, mention_id: str, mention_handle: str
    ) -> None:
        await self._client.agent_api_messages.create_agent_chat_message(
            room_id,
            message=ChatMessageRequest(
                content=content,
                mentions=[
                    ChatMessageRequestMentionsItem(id=mention_id, handle=mention_handle)
                ],
            ),
            request_options=DEFAULT_REQUEST_OPTIONS,
        )


@dataclass(frozen=True)
class EscalationRecord:
    correlation_id: str
    run_id: str
    job_id: str
    room_id: str | None
    expires_at: datetime
    state: str
    response_message_id: str | None


class SqliteEscalationStore:
    """Durable correlation state; never creates a second room for one run."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS band_escalations (
                    correlation_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    job_id TEXT NOT NULL,
                    room_id TEXT UNIQUE,
                    expires_at TEXT NOT NULL,
                    state TEXT NOT NULL,
                    response_message_id TEXT UNIQUE
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._path)
        connection.row_factory = sqlite3.Row
        return connection

    def get_by_run(self, run_id: str) -> EscalationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM band_escalations WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._record(row)

    def get_by_room(self, room_id: str) -> EscalationRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM band_escalations WHERE room_id = ?", (room_id,)
            ).fetchone()
        return self._record(row)

    def create(
        self, *, correlation_id: str, run_id: str, job_id: str, expires_at: datetime
    ) -> EscalationRecord:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR IGNORE INTO band_escalations "
                "(correlation_id, run_id, job_id, expires_at, state) "
                "VALUES (?, ?, ?, ?, 'creating')",
                (correlation_id, run_id, job_id, expires_at.isoformat()),
            )
        record = self.get_by_run(run_id)
        if record is None:
            raise EscalationError("Unable to persist the Band escalation correlation.")
        return record

    def assign_room(self, *, correlation_id: str, room_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE band_escalations SET room_id = ?, state = 'pending' "
                "WHERE correlation_id = ? AND room_id IS NULL",
                (room_id, correlation_id),
            )

    def fail(self, correlation_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE band_escalations SET state = 'failed' WHERE correlation_id = ?",
                (correlation_id,),
            )

    def claim_response(self, *, correlation_id: str, message_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE band_escalations SET response_message_id = ?, state = 'resuming' "
                "WHERE correlation_id = ? AND state = 'pending' AND response_message_id IS NULL",
                (message_id, correlation_id),
            )
        return cursor.rowcount == 1

    def complete_response(self, correlation_id: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "UPDATE band_escalations SET state = 'resumed' WHERE correlation_id = ?",
                (correlation_id,),
            )

    def claim_expiry(self, correlation_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE band_escalations SET state = 'expired' "
                "WHERE correlation_id = ? AND state = 'pending'",
                (correlation_id,),
            )
        return cursor.rowcount == 1

    @staticmethod
    def _record(row: sqlite3.Row | None) -> EscalationRecord | None:
        if row is None:
            return None
        return EscalationRecord(
            correlation_id=row["correlation_id"],
            run_id=row["run_id"],
            job_id=row["job_id"],
            room_id=row["room_id"],
            expires_at=datetime.fromisoformat(row["expires_at"]),
            state=row["state"],
            response_message_id=row["response_message_id"],
        )


class EscalationResumer(Protocol):
    async def resume(
        self,
        *,
        job_id: str,
        run_id: str,
        correlation_id: str,
        decision: HumanDecision,
        response: str,
    ) -> None: ...

    async def expire(self, *, job_id: str, run_id: str, correlation_id: str) -> None: ...


class JobQueueEscalationResumer:
    """Releases the original 202 Job through the durable queue boundary."""

    def __init__(self, *, jobs: JobRepository, queue: QueueBoundary) -> None:
        self._jobs = jobs
        self._queue = queue

    async def resume(
        self,
        *,
        job_id: str,
        run_id: str,
        correlation_id: str,
        decision: HumanDecision,
        response: str,
    ) -> None:
        job = await self._require_job(job_id)
        if decision is HumanDecision.REJECT:
            await self._jobs.save(
                job.model_copy(
                    update={
                        "status": JobStatus.FAILED,
                        "updated_at": datetime.now(UTC),
                        "failure": "Band escalation rejected by the configured human responder.",
                    }
                )
            )
            return
        resumed = job.model_copy(
            update={
                "status": JobStatus.QUEUED,
                "updated_at": datetime.now(UTC),
                "result_ref": f"band://escalations/{correlation_id}",
                "failure": None,
            }
        )
        await self._jobs.save(resumed)
        await self._queue.enqueue(resumed)

    async def expire(self, *, job_id: str, run_id: str, correlation_id: str) -> None:
        job = await self._require_job(job_id)
        await self._jobs.save(
            job.model_copy(
                update={
                    "status": JobStatus.FAILED,
                    "updated_at": datetime.now(UTC),
                    "failure": "Band escalation expired without a valid human response.",
                }
            )
        )

    async def _require_job(self, job_id: str):
        job = await self._jobs.get(job_id)
        if job is None:
            raise EscalationError(f"Waiting job {job_id} was not found.")
        return job


class BandEscalationPort:
    def __init__(
        self, *, config: EscalationConfig, store: SqliteEscalationStore, rooms: BandRooms
    ) -> None:
        self._config = config
        self._store = store
        self._rooms = rooms
        self._lock = asyncio.Lock()

    async def escalate(self, run: RunOutcome, *, job_id: str) -> str:
        correlation_id = f"escalation-{run.id}"
        async with self._lock:
            existing = self._store.get_by_run(run.id)
            if existing is not None:
                if existing.state == "failed":
                    raise EscalationError(
                        "The existing Band escalation failed and requires operator repair."
                    )
                return existing.correlation_id
            record = self._store.create(
                correlation_id=correlation_id,
                run_id=run.id,
                job_id=job_id,
                expires_at=datetime.now(UTC) + self._config.response_ttl,
            )
            try:
                room_id = await self._rooms.create_room(title=f"Evox escalation {correlation_id}")
                await self._rooms.add_participant(
                    room_id=room_id, participant_id=self._config.human_id
                )
                content = (
                    f"@{self._config.human_handle} approval required. "
                    f"correlation_id={correlation_id}. "
                    "Reply with JSON: {correlation_id, decision: approve|reject, reason, "
                    "responded_at}."
                )
                await self._rooms.send_message(
                    room_id=room_id,
                    content=content,
                    mention_id=self._config.human_id,
                    mention_handle=self._config.human_handle,
                )
                self._store.assign_room(correlation_id=record.correlation_id, room_id=room_id)
            except Exception:
                self._store.fail(correlation_id)
                raise
        return correlation_id


class BandResponseProcessor:
    def __init__(
        self, *, config: EscalationConfig, store: SqliteEscalationStore, resumer: EscalationResumer
    ) -> None:
        self._config = config
        self._store = store
        self._resumer = resumer

    async def process(
        self, *, message_id: str, room_id: str, sender_id: str, sender_type: str, content: str
    ) -> bool:
        if sender_type != "user" or sender_id != self._config.human_id:
            return False
        record = self._store.get_by_room(room_id)
        if record is None or record.state not in {"pending", "resuming", "resumed"}:
            return False
        try:
            response = HumanResponse.model_validate_json(content)
        except ValidationError:
            return False
        if response.correlation_id != record.correlation_id:
            return False
        if datetime.now(UTC) > record.expires_at:
            if self._store.claim_expiry(record.correlation_id):
                await self._resumer.expire(
                    job_id=record.job_id,
                    run_id=record.run_id,
                    correlation_id=record.correlation_id,
                )
            raise EscalationExpired(f"Escalation {record.correlation_id} expired before response.")
        if not self._store.claim_response(
            correlation_id=record.correlation_id, message_id=message_id
        ):
            return True
        try:
            await self._resumer.resume(
                job_id=record.job_id,
                run_id=record.run_id,
                correlation_id=record.correlation_id,
                decision=response.decision,
                response=response.reason,
            )
        except Exception:
            raise
        self._store.complete_response(record.correlation_id)
        return True


class _ResponseAdapter(SimpleAdapter[HistoryProvider]):
    def __init__(self, processor: BandResponseProcessor) -> None:
        super().__init__()
        self._processor = processor

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: object,
        history: HistoryProvider,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        await self._processor.process(
            message_id=msg.id,
            room_id=room_id,
            sender_id=msg.sender_id,
            sender_type=msg.sender_type,
            content=msg.content,
        )


class BandEscalationWorker:
    """The process entry point: Band's SDK maintains the WebSocket for its lifetime."""

    def __init__(self, *, config: EscalationConfig, processor: BandResponseProcessor) -> None:
        self._agent = Agent.create(
            adapter=_ResponseAdapter(processor),
            agent_id=config.agent_id,
            api_key=config.api_key,
            ws_url=config.ws_url,
            rest_url=config.rest_url,
        )

    async def run_forever(self) -> None:
        await self._agent.run()
