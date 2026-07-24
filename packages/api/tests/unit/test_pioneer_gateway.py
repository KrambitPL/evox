import json

import httpx
import pytest
from pydantic import BaseModel

from evox_api.adapters.pioneer.gateway import (
    PioneerGatewayError,
    PioneerModelGateway,
    PioneerSettings,
)
from evox_api.domain.errors import IntegrationUnavailable


def _client(handler: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=handler, base_url="https://api.pioneer.ai/v1")


def _completion(content: str, *, request_id: str = "pioneer-request-1") -> dict[str, object]:
    return {
        "id": "chatcmpl-1",
        "object": "chat.completion",
        "created": 1_721_000_000,
        "model": "pioneer-model",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
        "usage": {
            "prompt_tokens": 12,
            "completion_tokens": 8,
            "total_tokens": 20,
            "cost": {"input": 0.001, "output": 0.002, "total": 0.003},
        },
        "request_id": request_id,
    }


def test_settings_fail_closed_without_a_pioneer_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PIONEER_API_KEY", raising=False)

    with pytest.raises(IntegrationUnavailable):
        PioneerSettings.from_environment()


@pytest.mark.asyncio
async def test_generate_uses_pioneer_wire_contract_and_captures_observability() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_completion("A real answer"))

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret", max_attempts=1),
        client=_client(httpx.MockTransport(handler)),
    )

    response = await gateway.generate_response(
        model="pioneer-model", prompt="Give the answer", correlation_id="run-123"
    )

    assert response.content == "A real answer"
    assert response.correlation_id == "run-123"
    assert response.provider_request_id == "pioneer-request-1"
    assert response.usage.total_tokens == 20
    assert response.usage.cost_usd == 0.003
    assert response.latency_ms >= 0
    assert requests[0].url == httpx.URL("https://api.pioneer.ai/v1/chat/completions")
    assert requests[0].headers["x-api-key"] == "pioneer-secret"
    assert requests[0].headers["x-request-id"] == "run-123"
    assert json.loads(requests[0].content) == {
        "model": "pioneer-model",
        "messages": [{"role": "user", "content": "Give the answer"}],
        "stream": False,
    }


class _Score(BaseModel):
    score: int


@pytest.mark.asyncio
async def test_structured_output_is_validated_against_the_requested_schema() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=_completion('{"score": 7}'))

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret", max_attempts=1),
        client=_client(httpx.MockTransport(handler)),
    )

    response = await gateway.generate_structured(
        model="pioneer-model",
        prompt="Score",
        schema=_Score,
        pioneer_schema={"structures": {"score": "integer"}},
    )

    assert response.value == _Score(score=7)
    assert response.response.usage.prompt_tokens == 12
    assert json.loads(requests[0].content)["schema"] == {"structures": {"score": "integer"}}


@pytest.mark.asyncio
async def test_invalid_structured_output_fails_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion('{"score": "not-a-number"}'))

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret", max_attempts=1),
        client=_client(httpx.MockTransport(handler)),
    )

    with pytest.raises(PioneerGatewayError, match="structured output"):
        await gateway.generate_structured(model="pioneer-model", prompt="Score", schema=_Score)


@pytest.mark.asyncio
async def test_retries_only_retryable_failures_with_a_strict_limit() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, json={"error": {"message": "temporarily unavailable"}})
        return httpx.Response(200, json=_completion("Recovered"))

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret", max_attempts=3, retry_backoff_seconds=0),
        client=_client(httpx.MockTransport(handler)),
    )

    assert await gateway.generate("pioneer-model", "Retry") == "Recovered"
    assert attempts == 3


@pytest.mark.asyncio
async def test_errors_are_redacted_and_do_not_leak_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "key pioneer-secret rejected"}})

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret", max_attempts=1),
        client=_client(httpx.MockTransport(handler)),
    )

    with pytest.raises(PioneerGatewayError) as raised:
        await gateway.generate("pioneer-model", "Nope")

    assert "pioneer-secret" not in str(raised.value)
    assert raised.value.code == "pioneer_request_failed"


@pytest.mark.asyncio
async def test_health_check_reports_the_real_provider_state() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"object": "list", "data": [{"id": "pioneer-model"}]})

    gateway = PioneerModelGateway(
        PioneerSettings(api_key="pioneer-secret"), client=_client(httpx.MockTransport(handler))
    )

    health = await gateway.health_check()

    assert health.healthy is True
    assert health.models == ("pioneer-model",)
