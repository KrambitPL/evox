# Agent 5 handoff — Pioneer gateway

Date: 2026-07-24

## Delivered

- Added the fail-closed `PioneerModelGateway` at
  `packages/api/src/evox_api/adapters/pioneer/`.
- The only supported production route is `https://api.pioneer.ai/v1`; settings reject
  missing API keys, alternate base URLs, and unsafe retry configuration.
- Requests use Pioneer's required `X-API-Key` header and propagate a generated or
  caller-supplied `X-Request-ID` correlation value.
- Added response telemetry for token usage, optional USD cost, provider request ID, and
  measured latency; retries are limited to three attempts and retryable transport/HTTP
  failures only.
- Added validated structured-output parsing and a deliberate `pioneer_schema` field for
  Pioneer's OpenAI-compatible `schema` extension. No arbitrary provider extra body is
  accepted.
- Provider errors are reduced to safe status/correlation data, and the health check
  checks Pioneer's actual `/models` endpoint.

## Verification

`make test-unit` and `make lint` both pass: 25 tests total, including seven Pioneer
adapter tests with full representative OpenAI-compatible wire responses isolated in tests.

## Integration note

Construct the gateway with `PioneerSettings.from_environment()` only where the
application composition root has access to server-side secret configuration. A missing
`PIONEER_API_KEY` raises `IntegrationUnavailable`; do not catch it to select another
model provider.
