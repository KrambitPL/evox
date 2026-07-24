from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import pytest

from evox_api.adapters.actian.outcome_memory import (
    ActianOutcomeMemory,
    OutcomeMemoryContext,
)
from evox_api.domain.contracts import RunOutcome, RunStatus
from evox_api.domain.errors import IntegrationUnavailable


class FakeCollections:
    def __init__(self) -> None:
        self.created: list[tuple[str, object]] = []

    async def exists(self, collection: str) -> bool:
        return False

    async def create(self, collection: str, *, vectors_config: object) -> None:
        self.created.append((collection, vectors_config))


class FakePoints:
    def __init__(self) -> None:
        self.upserts: list[tuple[str, list[object]]] = []
        self.searches: list[dict[str, object]] = []
        self.results: list[object] = []

    async def upsert(self, collection: str, points: list[object]) -> None:
        self.upserts.append((collection, points))

    async def search(self, collection: str, vector: list[float], **kwargs: object) -> list[object]:
        kwargs["vector"] = vector
        self.searches.append({"collection": collection, **kwargs})
        return self.results


class FakeClient:
    def __init__(self) -> None:
        self.collections = FakeCollections()
        self.points = FakePoints()

    async def connect(self) -> None:
        return None

    async def health_check(self) -> dict[str, str]:
        return {"title": "Actian VectorAI DB"}


class Result:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload


def outcome(status: RunStatus = RunStatus.SUCCEEDED) -> RunOutcome:
    return RunOutcome(
        id="run_001",
        system_id="system_issue_resolver_v1",
        evaluation_case_id="case_001",
        output="The issue is resolved with cited evidence.",
        trace_refs=("s3://evox-traces/run_001.json",),
        evidence_refs=("s3://evox-evidence/run_001.json",),
        score_components={
            "disposition": 1.0,
            "required_facts": 0.8,
            "citation_quality": 0.9,
            "appropriate_escalation": 1.0,
        },
        cost_usd=0.03,
        latency_ms=820,
        status=status,
        completed_at=datetime(2026, 7, 24, tzinfo=UTC),
    )


async def embed(text: str) -> list[float]:
    assert text
    return [0.1, 0.2, 0.3]


async def context_for(run: RunOutcome) -> OutcomeMemoryContext:
    assert run.system_id == "system_issue_resolver_v1"
    return OutcomeMemoryContext(
        mission_id="mission_issue_resolver",
        system_version=3,
        split="held_out",
        retention_until=datetime(2027, 7, 24, tzinfo=UTC),
    )


@pytest.mark.anyio
async def test_record_stores_embedded_outcome_with_required_metadata_and_tenant() -> None:
    client = FakeClient()
    memory = ActianOutcomeMemory(
        client=client,  # type: ignore[arg-type]
        collection="evox_outcomes",
        vector_size=3,
        embed=embed,
        context_for_outcome=context_for,
    )

    await memory.record(outcome(), tenant_id="tenant_alpha")

    stored = client.points.upserts[0][1][0]
    assert stored.id == str(uuid5(NAMESPACE_URL, "evox:tenant_alpha:run_001"))
    assert stored.vector == [0.1, 0.2, 0.3]
    assert stored.payload == {
        "tenant_id": "tenant_alpha",
        "run_id": "run_001",
        "mission_id": "mission_issue_resolver",
        "system_id": "system_issue_resolver_v1",
        "system_version": 3,
        "split": "held_out",
        "status": "succeeded",
        "outcome_kind": "successful",
        "score": 0.91,
        "failure_labels": [],
        "evidence_refs": ["s3://evox-evidence/run_001.json"],
        "retention_until": "2027-07-24T00:00:00+00:00",
        "outcome": outcome().model_dump(mode="json"),
    }


@pytest.mark.anyio
async def test_recall_filters_by_tenant_and_requested_success_or_failure_state() -> None:
    client = FakeClient()
    client.points.results = [Result({"outcome": outcome().model_dump(mode="json")})]
    memory = ActianOutcomeMemory(
        client=client,  # type: ignore[arg-type]
        collection="evox_outcomes",
        vector_size=3,
        embed=embed,
        context_for_outcome=context_for,
    )

    results = await memory.recall(
        "Resolve the issue with evidence.",
        tenant_id="tenant_alpha",
        filters={
            "mission_id": "mission_issue_resolver",
            "outcome_kind": "successful",
            "system_version": "3",
        },
    )

    assert results == (outcome(),)
    query = client.points.searches[0]
    assert query["collection"] == "evox_outcomes"
    assert query["vector"] == [0.1, 0.2, 0.3]
    assert _filter_equals(query["filter"], "tenant_id", "tenant_alpha")
    assert _filter_equals(query["filter"], "mission_id", "mission_issue_resolver")
    assert _filter_equals(query["filter"], "outcome_kind", "successful")
    assert _filter_equals(query["filter"], "system_version", 3)


@pytest.mark.anyio
async def test_recall_rejects_unknown_filters_to_prevent_unscoped_queries() -> None:
    memory = ActianOutcomeMemory(
        client=FakeClient(),  # type: ignore[arg-type]
        collection="evox_outcomes",
        vector_size=3,
        embed=embed,
        context_for_outcome=context_for,
    )

    with pytest.raises(ValueError, match="Unsupported outcome-memory filters"):
        await memory.recall(
            "find failure", tenant_id="tenant_alpha", filters={"tenant_id": "other"}
        )


@pytest.mark.anyio
async def test_unavailable_actian_server_fails_closed() -> None:
    class UnavailableClient(FakeClient):
        async def health_check(self) -> dict[str, str]:
            raise OSError("connection refused")

    memory = ActianOutcomeMemory(
        client=UnavailableClient(),  # type: ignore[arg-type]
        collection="evox_outcomes",
        vector_size=3,
        embed=embed,
        context_for_outcome=context_for,
    )

    with pytest.raises(IntegrationUnavailable, match="Actian integration is not configured"):
        await memory.record(outcome(), tenant_id="tenant_alpha")


def _filter_equals(filter_: object, key: str, value: str | int) -> bool:
    return any(
        condition.field is not None
        and condition.field.key == key
        and condition.field.match is not None
        and (condition.field.match.keyword == value or condition.field.match.integer == value)
        for condition in filter_.must
    )
