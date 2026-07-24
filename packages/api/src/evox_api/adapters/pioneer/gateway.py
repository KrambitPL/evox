"""Fail-closed adapter for Pioneer's OpenAI-compatible model gateway."""

import asyncio
import json
import os
import time
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from evox_api.domain.errors import DomainError, IntegrationUnavailable

_PIONEER_BASE_URL = "https://api.pioneer.ai/v1"
_RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
_Schema = TypeVar("_Schema", bound=BaseModel)


class PioneerGatewayError(DomainError):
    """A safe-to-surface Pioneer failure that never includes provider payloads."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(code=code, message=message, details=details)


@dataclass(frozen=True)
class PioneerSettings:
    api_key: str
    base_url: str = _PIONEER_BASE_URL
    timeout_seconds: float = 30.0
    max_attempts: int = 2
    retry_backoff_seconds: float = 0.25

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise IntegrationUnavailable("pioneer")
        if self.base_url.rstrip("/") != _PIONEER_BASE_URL:
            raise PioneerGatewayError(
                "invalid_pioneer_configuration",
                "Pioneer base URL must be the configured Pioneer endpoint.",
            )
        if self.timeout_seconds <= 0:
            raise PioneerGatewayError(
                "invalid_pioneer_configuration", "Pioneer timeout must be greater than zero."
            )
        if not 1 <= self.max_attempts <= 3:
            raise PioneerGatewayError(
                "invalid_pioneer_configuration",
                "Pioneer max_attempts must be between one and three.",
            )
        if self.retry_backoff_seconds < 0:
            raise PioneerGatewayError(
                "invalid_pioneer_configuration", "Pioneer retry backoff cannot be negative."
            )

    @classmethod
    def from_environment(cls) -> "PioneerSettings":
        api_key = os.environ.get("PIONEER_API_KEY", "")
        if not api_key.strip():
            raise IntegrationUnavailable("pioneer")
        return cls(api_key=api_key)


@dataclass(frozen=True)
class PioneerUsage:
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float | None


@dataclass(frozen=True)
class PioneerResponse:
    content: str
    model: str
    correlation_id: str
    provider_request_id: str | None
    usage: PioneerUsage
    latency_ms: float


@dataclass(frozen=True)
class PioneerStructuredResponse(Generic[_Schema]):
    value: _Schema
    response: PioneerResponse


@dataclass(frozen=True)
class PioneerHealth:
    healthy: bool
    models: tuple[str, ...]
    latency_ms: float


class PioneerModelGateway:
    """ModelGateway implementation that is pinned to Pioneer and has no fallback route."""

    def __init__(
        self, settings: PioneerSettings, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.base_url,
            timeout=httpx.Timeout(settings.timeout_seconds),
        )

    async def generate(self, model: str, prompt: str) -> str:
        response = await self.generate_response(model=model, prompt=prompt)
        return response.content

    async def generate_response(
        self,
        *,
        model: str,
        prompt: str,
        correlation_id: str | None = None,
        pioneer_schema: Mapping[str, Any] | None = None,
    ) -> PioneerResponse:
        if not model.strip() or not prompt.strip():
            raise PioneerGatewayError(
                "invalid_pioneer_request", "Pioneer model and prompt must both be non-empty."
            )
        request_id = correlation_id or str(uuid.uuid4())
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        if pioneer_schema is not None:
            self._validate_pioneer_schema(pioneer_schema)
            payload["schema"] = dict(pioneer_schema)
        wire_response, latency_ms = await self._post_completion(payload, request_id)
        return self._parse_response(
            wire_response, model=model, correlation_id=request_id, latency_ms=latency_ms
        )

    async def generate_structured(
        self,
        *,
        model: str,
        prompt: str,
        schema: type[_Schema],
        pioneer_schema: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> PioneerStructuredResponse[_Schema]:
        response = await self.generate_response(
            model=model,
            prompt=prompt,
            correlation_id=correlation_id,
            pioneer_schema=pioneer_schema,
        )
        try:
            value = schema.model_validate_json(response.content)
        except (ValidationError, ValueError) as error:
            raise PioneerGatewayError(
                "invalid_pioneer_structured_output",
                "Pioneer returned invalid structured output.",
                details={"correlation_id": response.correlation_id},
            ) from error
        return PioneerStructuredResponse(value=value, response=response)

    async def health_check(self) -> PioneerHealth:
        started = time.perf_counter()
        try:
            response = await self._client.get(
                "/models", headers=self._headers(correlation_id=str(uuid.uuid4()))
            )
            response.raise_for_status()
            body = response.json()
            models = tuple(
                item["id"]
                for item in body.get("data", [])
                if isinstance(item, Mapping) and isinstance(item.get("id"), str)
            )
            return PioneerHealth(True, models, self._elapsed_ms(started))
        except (httpx.HTTPError, ValueError):
            return PioneerHealth(False, (), self._elapsed_ms(started))

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _post_completion(
        self, payload: dict[str, Any], correlation_id: str
    ) -> tuple[dict[str, Any], float]:
        for attempt in range(1, self._settings.max_attempts + 1):
            started = time.perf_counter()
            try:
                response = await self._client.post(
                    "/chat/completions", json=payload, headers=self._headers(correlation_id)
                )
            except httpx.RequestError as error:
                if attempt == self._settings.max_attempts:
                    raise PioneerGatewayError(
                        "pioneer_unavailable",
                        "Pioneer request could not be completed.",
                        details={"correlation_id": correlation_id},
                    ) from error
                await self._retry_delay(attempt)
                continue
            if (
                response.status_code in _RETRYABLE_STATUS_CODES
                and attempt < self._settings.max_attempts
            ):
                await self._retry_delay(attempt)
                continue
            if response.is_error:
                raise PioneerGatewayError(
                    "pioneer_request_failed",
                    f"Pioneer request failed (HTTP {response.status_code}).",
                    details={"correlation_id": correlation_id, "status_code": response.status_code},
                )
            try:
                body = response.json()
            except ValueError as error:
                raise PioneerGatewayError(
                    "invalid_pioneer_response",
                    "Pioneer returned a non-JSON response.",
                    details={"correlation_id": correlation_id},
                ) from error
            if not isinstance(body, dict):
                raise PioneerGatewayError(
                    "invalid_pioneer_response",
                    "Pioneer returned an invalid response shape.",
                    details={"correlation_id": correlation_id},
                )
            return body, self._elapsed_ms(started)
        raise AssertionError("Pioneer retry loop must return or raise")

    def _parse_response(
        self, body: dict[str, Any], *, model: str, correlation_id: str, latency_ms: float
    ) -> PioneerResponse:
        try:
            content = body["choices"][0]["message"]["content"]
            usage = body["usage"]
            if not isinstance(content, str) or not isinstance(usage, Mapping):
                raise TypeError
            parsed_usage = PioneerUsage(
                prompt_tokens=self._token_count(usage, "prompt_tokens"),
                completion_tokens=self._token_count(usage, "completion_tokens"),
                total_tokens=self._token_count(usage, "total_tokens"),
                cost_usd=self._cost(usage.get("cost")),
            )
        except (IndexError, KeyError, TypeError, ValueError) as error:
            raise PioneerGatewayError(
                "invalid_pioneer_response",
                "Pioneer returned an invalid completion response.",
                details={"correlation_id": correlation_id},
            ) from error
        provider_request_id = body.get("request_id") or body.get("id")
        return PioneerResponse(
            content=content,
            model=model,
            correlation_id=correlation_id,
            provider_request_id=provider_request_id
            if isinstance(provider_request_id, str)
            else None,
            usage=parsed_usage,
            latency_ms=latency_ms,
        )

    def _headers(self, correlation_id: str) -> dict[str, str]:
        return {
            "X-API-Key": self._settings.api_key,
            "X-Request-ID": correlation_id,
            "Content-Type": "application/json",
        }

    async def _retry_delay(self, attempt: int) -> None:
        await asyncio.sleep(self._settings.retry_backoff_seconds * attempt)

    @staticmethod
    def _token_count(usage: Mapping[str, Any], name: str) -> int:
        value = usage[name]
        if not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} is invalid")
        return value

    @staticmethod
    def _cost(value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, Mapping):
            total = value.get("total")
            if isinstance(total, (int, float)) and not isinstance(total, bool):
                return float(total)
        raise ValueError("cost is invalid")

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        return (time.perf_counter() - started) * 1_000

    @staticmethod
    def _validate_pioneer_schema(schema: Mapping[str, Any]) -> None:
        if not schema:
            raise PioneerGatewayError(
                "invalid_pioneer_request", "Pioneer schema must not be empty."
            )
        try:
            json.dumps(dict(schema))
        except (TypeError, ValueError) as error:
            raise PioneerGatewayError(
                "invalid_pioneer_request", "Pioneer schema must be JSON serializable."
            ) from error
