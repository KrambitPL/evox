# Band escalation design — 2026-07-24

The escalation adapter uses the official pinned `band-sdk` (`band` import) for
Band REST actions and a long-lived `Agent.run()` WebSocket worker for inbound
responses. It does not create request-scoped background tasks.

Each escalated run is assigned `escalation-{run_id}` and persisted in SQLite
before any Band room request. Repeated calls return the existing correlation,
which prevents duplicate room creation. A failed in-flight request remains
failed for operator repair rather than silently creating another room.

The worker accepts only messages from the configured Band human user ID, only
in a correlated room, and only when the message validates as the strict JSON
response schema. Valid approvals requeue the supplied waiting Job through the
real repository and queue ports; rejection and expiry fail it. Message IDs and
state transitions make duplicate delivery idempotent.

Band credentials are environment-only (`EVOX_BAND_AGENT_ID`,
`EVOX_BAND_API_KEY`, `EVOX_BAND_HUMAN_ID`, `EVOX_BAND_HUMAN_HANDLE`). Missing
configuration raises the explicit `IntegrationUnavailable("band")` error.
