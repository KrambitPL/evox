from __future__ import annotations

import asyncio
import hashlib
import os
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from evox_api.domain.errors import IntegrationUnavailable
from evox_api.ports.sponsors import KnowledgeCitation, KnowledgeResult

DEFAULT_SENSO_BASE_URL = "https://apiv2.senso.ai/api/v1"


class SensoIntegrationError(ValueError):
    """A Senso response cannot safely be used as product knowledge."""


@dataclass(frozen=True)
class SensoSettings:
    api_key: str
    base_url: str = DEFAULT_SENSO_BASE_URL
    timeout_seconds: float = 15.0
    poll_interval_seconds: float = 1.0
    max_poll_attempts: int = 60

    @classmethod
    def from_environment(cls) -> SensoSettings:
        api_key = os.environ.get("SENSO_API_KEY", "")
        if not api_key.strip():
            raise IntegrationUnavailable("senso")
        return cls(api_key=api_key)

    def __post_init__(self) -> None:
        if not self.api_key.strip():
            raise IntegrationUnavailable("senso")
        invalid_polling = self.poll_interval_seconds < 0 or self.max_poll_attempts < 1
        if self.timeout_seconds <= 0 or invalid_polling:
            raise ValueError("Senso timeout and polling settings must be positive.")


@dataclass(frozen=True)
class SensoDocument:
    filename: str
    content: bytes
    content_type: str
    source_url: str
    tenant_id: str

    def __post_init__(self) -> None:
        required_values = (
            self.filename,
            self.content,
            self.content_type,
            self.source_url,
            self.tenant_id,
        )
        if not all(required_values):
            raise ValueError("Senso documents require content, source URL, and tenant context.")


@dataclass(frozen=True)
class SensoIngestedDocument:
    content_id: str
    kb_node_id: str
    source_url: str
    tenant_id: str


class SensoAdapter:
    """Typed, fail-closed adapter for Senso's configured organization API."""

    def __init__(self, settings: SensoSettings, *, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings
        self._client = client or httpx.AsyncClient(
            base_url=settings.base_url.rstrip("/"),
            headers={"X-API-Key": settings.api_key},
            timeout=httpx.Timeout(settings.timeout_seconds),
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if not self._client.is_closed:
            await self._client.aclose()

    async def health_check(self) -> None:
        await self._request_json("GET", "/org/kb/find", params={"q": "evox-health-check"})

    async def ingest(self, document: SensoDocument) -> SensoIngestedDocument:
        upload = await self._request_json(
            "POST",
            "/org/kb/upload",
            json={
                "files": [
                    {
                        "filename": document.filename,
                        "file_size_bytes": len(document.content),
                        "content_type": document.content_type,
                        "content_hash_md5": hashlib.md5(document.content).hexdigest(),
                    }
                ]
            },
        )
        result = self._single_upload_result(upload)
        content_id = self._required_string(result, "content_id", "upload result")
        upload_url = self._required_string(result, "upload_url", "upload result")
        await self._upload_bytes(upload_url, document)
        node_id = await self._resolve_node_id(content_id, document.filename)
        await self._wait_for_completion(node_id)
        return SensoIngestedDocument(
            content_id=content_id,
            kb_node_id=node_id,
            source_url=document.source_url,
            tenant_id=document.tenant_id,
        )

    async def retrieve(
        self, query: str, *, tenant_id: str, filters: Mapping[str, str]
    ) -> tuple[KnowledgeResult, ...]:
        if not query.strip() or not tenant_id.strip():
            raise ValueError("Senso queries require a query and tenant context.")
        effective_filters = {"tenant_id": tenant_id, **dict(filters)}
        response = await self._request_json(
            "POST",
            "/search",
            json={
                "query": query,
                "max_results": 10,
                "filters": effective_filters,
            },
        )
        raw_results = response.get("results")
        if not isinstance(raw_results, list):
            raise SensoIntegrationError("Senso search response has no results list.")
        return tuple(self._knowledge_result(item, tenant_id) for item in raw_results)

    async def _upload_bytes(self, upload_url: str, document: SensoDocument) -> None:
        try:
            response = await self._client.put(
                upload_url,
                content=document.content,
                headers={"Content-Type": document.content_type},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SensoIntegrationError("Senso document upload failed.") from exc

    async def _resolve_node_id(self, content_id: str, filename: str) -> str:
        payload = await self._request_json("GET", "/org/kb/find", params={"q": filename})
        nodes = payload.get("nodes")
        if not isinstance(nodes, list):
            raise SensoIntegrationError("Senso KB lookup returned malformed nodes.")
        for node in nodes:
            if isinstance(node, dict) and node.get("content_id") == content_id:
                return self._required_string(node, "kb_node_id", "KB node")
        raise SensoIntegrationError("Senso KB lookup did not return the uploaded document node.")

    async def _wait_for_completion(self, node_id: str) -> None:
        for attempt in range(self._settings.max_poll_attempts):
            payload = await self._request_json("GET", f"/org/kb/nodes/{node_id}/content")
            status = payload.get("processing_status")
            if status == "complete":
                return
            if status in {"failed", "expired", "cancelled"}:
                raise SensoIntegrationError("Senso ingestion is incomplete.")
            if not isinstance(status, str):
                raise SensoIntegrationError("Senso ingestion status is malformed.")
            if attempt < self._settings.max_poll_attempts - 1:
                await asyncio.sleep(self._settings.poll_interval_seconds)
        raise SensoIntegrationError("Senso ingestion timed out before completion.")

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = await self._client.request(method, path, **kwargs)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SensoIntegrationError("Senso request failed or returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise SensoIntegrationError("Senso response must be a JSON object.")
        return payload

    @staticmethod
    def _single_upload_result(payload: dict[str, Any]) -> dict[str, Any]:
        results = payload.get("results")
        if not isinstance(results, list) or len(results) != 1 or not isinstance(results[0], dict):
            raise SensoIntegrationError("Senso upload response must contain one upload result.")
        return results[0]

    def _knowledge_result(self, item: Any, tenant_id: str) -> KnowledgeResult:
        if not isinstance(item, dict):
            raise SensoIntegrationError("Senso search result is malformed.")
        content = self._required_string(item, "content", "search result")
        citation = item.get("citation")
        if not isinstance(citation, dict):
            raise SensoIntegrationError("Senso search result has a malformed citation.")
        freshness = self._required_string(citation, "freshness", "citation")
        try:
            retrieved_at = datetime.fromisoformat(freshness.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SensoIntegrationError("Senso citation freshness is malformed.") from exc
        citation_tenant = self._required_string(citation, "tenant_id", "citation")
        if citation_tenant != tenant_id:
            raise SensoIntegrationError(
                "Senso citation tenant does not match the requested tenant."
            )
        return KnowledgeResult(
            content=content,
            citations=(
                KnowledgeCitation(
                    citation_id=self._required_string(citation, "citation_id", "citation"),
                    document_id=self._required_string(citation, "document_id", "citation"),
                    source_uri=self._required_string(citation, "source_url", "citation"),
                    source_title=self._required_string(citation, "source_title", "citation"),
                    retrieved_at=retrieved_at,
                    tenant_id=citation_tenant,
                ),
            ),
        )

    @staticmethod
    def _required_string(payload: dict[str, Any], field: str, context: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise SensoIntegrationError(f"Senso {context} field {field!r} is malformed.")
        return value
