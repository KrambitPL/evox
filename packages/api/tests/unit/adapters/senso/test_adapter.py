import json
from datetime import UTC, datetime

import httpx
import pytest

from evox_api.adapters.senso import SensoAdapter, SensoDocument, SensoSettings
from evox_api.domain.errors import IntegrationUnavailable


@pytest.mark.anyio
async def test_ingest_uploads_then_waits_for_the_real_kb_node_to_complete() -> None:
    requests: list[httpx.Request] = []
    poll_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal poll_count
        requests.append(request)
        if request.url.path == "/api/v1/org/kb/upload":
            assert request.headers["X-API-Key"] == "senso-secret"
            assert json.loads(request.content) == {
                "files": [
                    {
                        "filename": "policy.md",
                        "file_size_bytes": 13,
                        "content_type": "text/markdown",
                        "content_hash_md5": "ada9f408637703989c5038bea116b1b9",
                    }
                ]
            }
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"content_id": "content-1", "upload_url": "https://upload.test/file"}
                    ]
                },
            )
        if request.url == httpx.URL("https://upload.test/file"):
            assert request.headers["Content-Type"] == "text/markdown"
            assert request.content == b"refund policy"
            return httpx.Response(200)
        if request.url.path == "/api/v1/org/kb/find":
            assert request.url.params == httpx.QueryParams({"q": "policy.md"})
            return httpx.Response(
                200,
                json={"nodes": [{"content_id": "content-1", "kb_node_id": "node-1"}]},
            )
        if request.url.path == "/api/v1/org/kb/nodes/node-1/content":
            poll_count += 1
            status = "processing" if poll_count == 1 else "complete"
            return httpx.Response(200, json={"processing_status": status})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    adapter = SensoAdapter(
        SensoSettings(api_key="senso-secret", poll_interval_seconds=0),
        client=httpx.AsyncClient(
            base_url="https://apiv2.senso.ai/api/v1",
            headers={"X-API-Key": "senso-secret"},
            transport=httpx.MockTransport(handler),
        ),
    )

    result = await adapter.ingest(
        SensoDocument(
            filename="policy.md",
            content=b"refund policy",
            content_type="text/markdown",
            source_url="https://example.test/policy",
            tenant_id="tenant-a",
        )
    )

    assert result.content_id == "content-1"
    assert result.kb_node_id == "node-1"
    assert result.source_url == "https://example.test/policy"
    assert result.tenant_id == "tenant-a"
    assert poll_count == 2
    await adapter.aclose()


@pytest.mark.anyio
async def test_query_preserves_all_citation_provenance() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/search"
        assert json.loads(request.content) == {
            "query": "What is the refund window?",
            "max_results": 10,
            "filters": {"tenant_id": "tenant-a", "category": "policy"},
        }
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "content": "Refunds are available for 30 days.",
                        "citation": {
                            "citation_id": "cite-1",
                            "document_id": "document-1",
                            "source_url": "https://example.test/policy",
                            "source_title": "Refund Policy",
                            "tenant_id": "tenant-a",
                            "freshness": "2026-07-24T10:30:00Z",
                        },
                    }
                ]
            },
        )

    adapter = SensoAdapter(
        SensoSettings(api_key="senso-secret"),
        client=httpx.AsyncClient(
            base_url="https://apiv2.senso.ai/api/v1",
            headers={"X-API-Key": "senso-secret"},
            transport=httpx.MockTransport(handler),
        ),
    )

    results = await adapter.retrieve(
        "What is the refund window?", tenant_id="tenant-a", filters={"category": "policy"}
    )

    assert results[0].content == "Refunds are available for 30 days."
    citation = results[0].citations[0]
    assert citation.citation_id == "cite-1"
    assert citation.document_id == "document-1"
    assert citation.source_uri == "https://example.test/policy"
    assert citation.tenant_id == "tenant-a"
    assert citation.retrieved_at == datetime(2026, 7, 24, 10, 30, tzinfo=UTC)
    await adapter.aclose()


@pytest.mark.anyio
async def test_fails_closed_for_incomplete_ingestion_malformed_citations_and_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content"):
            return httpx.Response(200, json={"processing_status": "failed"})
        if request.url.path == "/api/v1/search":
            return httpx.Response(200, json={"results": [{"content": "answer", "citation": {}}]})
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")

    adapter = SensoAdapter(
        SensoSettings(api_key="senso-secret", poll_interval_seconds=0),
        client=httpx.AsyncClient(
            base_url="https://apiv2.senso.ai/api/v1",
            headers={"X-API-Key": "senso-secret"},
            transport=httpx.MockTransport(handler),
        ),
    )
    with pytest.raises(ValueError, match="incomplete"):
        await adapter._wait_for_completion("node-1")
    with pytest.raises(ValueError, match="citation"):
        await adapter.retrieve("question", tenant_id="tenant-a", filters={})
    await adapter.aclose()


@pytest.mark.anyio
async def test_fails_closed_when_senso_times_out() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Senso did not respond", request=request)

    adapter = SensoAdapter(
        SensoSettings(api_key="senso-secret"),
        client=httpx.AsyncClient(
            base_url="https://apiv2.senso.ai/api/v1",
            transport=httpx.MockTransport(handler),
        ),
    )

    with pytest.raises(ValueError, match="request failed"):
        await adapter.retrieve("question", tenant_id="tenant-a", filters={})
    await adapter.aclose()


def test_missing_senso_api_key_fails_closed() -> None:
    with pytest.raises(IntegrationUnavailable):
        SensoSettings(api_key="")
