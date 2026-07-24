from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from evox_api.domain.contracts import (
    BudgetPolicy,
    Capability,
    EvaluationDatasets,
    HitlPolicy,
    MissionContract,
)
from evox_api.main import ApplicationRuntime, create_app


class MissionStore:
    def __init__(self) -> None:
        self.missions: dict[str, MissionContract] = {}

    async def save(self, mission: MissionContract) -> None:
        self.missions[mission.id] = mission

    async def get(self, mission_id: str) -> MissionContract | None:
        return self.missions.get(mission_id)


class Repository:
    async def get(self, _: str) -> None:
        return None

    async def save(self, _: Any) -> None:
        return None


class Queue:
    async def enqueue(self, _: Any) -> None:
        return None


async def health() -> dict[str, Any]:
    return {
        "services": [
            {"name": "Pioneer", "status": "healthy", "detail": "Live models available."},
            {"name": "Actian", "status": "unavailable", "detail": "Not configured."},
        ]
    }


def mission() -> MissionContract:
    return MissionContract(
        id="mission-live-001",
        objective="Resolve a configured EvoAgentX issue",
        success_criteria=("Return a cited resolution or escalate",),
        allowed_capabilities=frozenset({Capability.MODEL_INFERENCE}),
        hard_constraints=("Do not change immutable policy",),
        budgets=BudgetPolicy(max_cost_usd=5, max_latency_ms=60_000, max_model_calls=20),
        evaluation_datasets=EvaluationDatasets(
            train_ref="corpus/train.json",
            dev_ref="corpus/dev.json",
            held_out_ref="corpus/release-gate/heldout.json",
        ),
        hitl_policy=HitlPolicy(required_for_escalation=True, owner_review_required=True),
    )


def runtime() -> ApplicationRuntime:
    repository = Repository()
    return ApplicationRuntime(
        missions=MissionStore(),
        jobs=repository,
        candidates=repository,
        queue=Queue(),
        integration_health=health,
    )


def test_real_runtime_persists_and_reads_missions() -> None:
    client = TestClient(create_app(runtime()))

    created = client.post("/v1/missions", json=mission().model_dump(mode="json"))
    loaded = client.get("/v1/missions/mission-live-001")

    assert created.status_code == 201
    assert loaded.status_code == 200
    assert loaded.json() == created.json()


def test_runtime_returns_truthful_partial_integration_health() -> None:
    response = TestClient(create_app(runtime())).get("/v1/integrations/health")

    assert response.status_code == 200
    assert response.json()["services"][0]["status"] == "healthy"
    assert response.json()["services"][1]["status"] == "unavailable"
