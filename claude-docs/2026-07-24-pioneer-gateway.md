# Pioneer gateway design record

The Pioneer adapter is pinned to `https://api.pioneer.ai/v1` and uses `X-API-Key`, based
on Pioneer's OpenAI-compatible API contract. It intentionally has no second provider or
environment-dependent fallback.

The existing `ModelGateway.generate(model, prompt)` port remains stable. The adapter adds
an opt-in richer response method for observability and structured validation without
forcing unrelated callers to adopt a new domain type.

Pioneer's `schema` extension is accepted only through an explicit `pioneer_schema`
parameter, checked for a non-empty JSON-serializable mapping. This preserves the provider
feature without turning the adapter into a blind pass-through for arbitrary fields.

Retries are limited to retryable transport failures and HTTP 408/409/429/5xx statuses, to
at most three attempts. Returned/surfaced errors never contain provider response bodies or
the API key.
