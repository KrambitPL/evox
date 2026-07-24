from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import NAMESPACE_URL, uuid5

from actian_vectorai import (
    AsyncVectorAIClient,
    Distance,
    Field,
    FilterBuilder,
    PointStruct,
    VectorParams,
)

from evox_api.domain.contracts import RunOutcome, RunStatus
from evox_api.domain.errors import IntegrationUnavailable
from evox_api.ports.sponsors import OutcomeMemoryPort

_SUPPORTED_FILTERS = frozenset(
    {"mission_id", "system_id", "system_version", "split", "outcome_kind", "status"}
)


class _Collections(Protocol):
    async def exists(self, name: str) -> bool: ...

    async def create(self, name: str, *, vectors_config: VectorParams) -> bool: ...


class _Points(Protocol):
    async def upsert(self, collection_name: str, points: list[PointStruct]) -> Any: ...

    async def search(
        self,
        collection_name: str,
        vector: list[float],
        *,
        limit: int,
        filter: Any,
        with_payload: bool,
    ) -> list[Any]: ...


class _ActianClient(Protocol):
    collections: _Collections
    points: _Points

    async def connect(self) -> None: ...

    async def health_check(self) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ActianOutcomeMemorySettings:
    url: str
    access_token: str
    collection: str
    vector_size: int
    tls: bool = True

    @classmethod
    def from_environment(cls) -> ActianOutcomeMemorySettings:
        url = os.getenv("ACTIAN_VECTORAI_URL")
        access_token = os.getenv("ACTIAN_VECTORAI_ACCESS_TOKEN")
        collection = os.getenv("EVOX_ACTIAN_OUTCOME_COLLECTION")
        vector_size = os.getenv("EVOX_ACTIAN_VECTOR_SIZE")
        if not all((url, access_token, collection, vector_size)):
            raise IntegrationUnavailable("actian")
        try:
            parsed_vector_size = int(vector_size)
        except ValueError as error:
            raise IntegrationUnavailable("actian") from error
        if parsed_vector_size < 1:
            raise IntegrationUnavailable("actian")
        return cls(
            url=url,
            access_token=access_token,
            collection=collection,
            vector_size=parsed_vector_size,
            tls=os.getenv("ACTIAN_VECTORAI_TLS", "true").lower() == "true",
        )

    def client(self) -> AsyncVectorAIClient:
        return AsyncVectorAIClient(url=self.url, access_token=self.access_token, tls=self.tls)


@dataclass(frozen=True)
class OutcomeMemoryContext:
    mission_id: str
    system_version: int
    split: str
    retention_until: datetime


EmbeddingFunction = Callable[[str], Awaitable[list[float]]]
OutcomeContextResolver = Callable[[RunOutcome], Awaitable[OutcomeMemoryContext]]


class ActianOutcomeMemory(OutcomeMemoryPort):
    """Persist and retrieve tenant-isolated run outcomes via Actian VectorAI DB."""

    def __init__(
        self,
        *,
        client: _ActianClient,
        collection: str,
        vector_size: int,
        embed: EmbeddingFunction,
        context_for_outcome: OutcomeContextResolver,
    ) -> None:
        if not collection or vector_size < 1:
            raise IntegrationUnavailable("actian")
        self._client = client
        self._collection = collection
        self._vector_size = vector_size
        self._embed = embed
        self._context_for_outcome = context_for_outcome
        self._collection_ready = False

    @classmethod
    def from_settings(
        cls,
        settings: ActianOutcomeMemorySettings,
        *,
        embed: EmbeddingFunction,
        context_for_outcome: OutcomeContextResolver,
    ) -> ActianOutcomeMemory:
        return cls(
            client=settings.client(),
            collection=settings.collection,
            vector_size=settings.vector_size,
            embed=embed,
            context_for_outcome=context_for_outcome,
        )

    async def record(self, outcome: RunOutcome, *, tenant_id: str) -> None:
        self._require_tenant(tenant_id)
        await self._ensure_collection()
        context = await self._context_for_outcome(outcome)
        vector = await self._vector_for(outcome.output)
        await self._call_actian(
            self._client.points.upsert(
                self._collection,
                [
                    PointStruct(
                        id=str(uuid5(NAMESPACE_URL, f"evox:{tenant_id}:{outcome.id}")),
                        vector=vector,
                        payload=self._payload(outcome, tenant_id=tenant_id, context=context),
                    )
                ],
            )
        )

    async def recall(
        self, query: str, *, tenant_id: str, filters: Mapping[str, str]
    ) -> tuple[RunOutcome, ...]:
        self._require_tenant(tenant_id)
        if not query:
            raise ValueError("Outcome-memory query must not be empty.")
        unsupported_filters = set(filters) - _SUPPORTED_FILTERS
        if unsupported_filters:
            raise ValueError(f"Unsupported outcome-memory filters: {sorted(unsupported_filters)}")
        await self._ensure_collection()
        vector = await self._vector_for(query)
        filter_builder = FilterBuilder().must(Field("tenant_id").eq(tenant_id))
        for key, value in filters.items():
            if not value:
                raise ValueError(f"Outcome-memory filter {key!r} must not be empty.")
            filter_builder.must(Field(key).eq(self._filter_value(key, value)))
        results = await self._call_actian(
            self._client.points.search(
                self._collection,
                vector,
                limit=10,
                filter=filter_builder.build(),
                with_payload=True,
            )
        )
        return tuple(self._outcome_from_result(result) for result in results)

    async def _ensure_collection(self) -> None:
        await self._call_actian(self._client.connect())
        await self._call_actian(self._client.health_check())
        if self._collection_ready:
            return
        exists = await self._call_actian(self._client.collections.exists(self._collection))
        if not exists:
            await self._call_actian(
                self._client.collections.create(
                    self._collection,
                    vectors_config=VectorParams(size=self._vector_size, distance=Distance.Cosine),
                )
            )
        self._collection_ready = True

    async def _vector_for(self, text: str) -> list[float]:
        vector = await self._embed(text)
        if len(vector) != self._vector_size:
            raise IntegrationUnavailable("actian")
        return vector

    async def _call_actian(self, operation: Awaitable[Any]) -> Any:
        try:
            return await operation
        except Exception as error:
            raise IntegrationUnavailable("actian") from error

    @staticmethod
    def _require_tenant(tenant_id: str) -> None:
        if not tenant_id:
            raise ValueError("tenant_id must not be empty.")

    @staticmethod
    def _filter_value(key: str, value: str) -> str | int:
        if key != "system_version":
            return value
        try:
            version = int(value)
        except ValueError as error:
            raise ValueError("Outcome-memory system_version must be an integer.") from error
        if version < 1:
            raise ValueError("Outcome-memory system_version must be positive.")
        return version

    @staticmethod
    def _payload(
        outcome: RunOutcome, *, tenant_id: str, context: OutcomeMemoryContext
    ) -> dict[str, Any]:
        failure_labels = [] if outcome.status is RunStatus.SUCCEEDED else [outcome.status.value]
        return {
            "tenant_id": tenant_id,
            "run_id": outcome.id,
            "mission_id": context.mission_id,
            "system_id": outcome.system_id,
            "system_version": context.system_version,
            "split": context.split,
            "status": outcome.status.value,
            "outcome_kind": "successful" if not failure_labels else "failed",
            "score": outcome.overall_score,
            "failure_labels": failure_labels,
            "evidence_refs": list(outcome.evidence_refs),
            "retention_until": context.retention_until.isoformat(),
            "outcome": outcome.model_dump(mode="json"),
        }

    @staticmethod
    def _outcome_from_result(result: Any) -> RunOutcome:
        try:
            return RunOutcome.model_validate(result.payload["outcome"])
        except Exception as error:
            raise IntegrationUnavailable("actian") from error
