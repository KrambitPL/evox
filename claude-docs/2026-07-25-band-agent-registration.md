# Band agent registration — 2026-07-25

The production Band external agent was registered through the official Human API using
the separately scoped human REST key already present in the local, gitignored `.env`.
Registration used `POST https://app.band.ai/api/v1/me/agents/register` with the name
`Evox Remote Human Escalation` and returned agent ID
`6eb62abe-f880-44d5-9ae2-2b8dc0f42b5c`.

The one-time agent API key was never printed, committed, or added to application logs.
It was stored as `EVOX_BAND_API_KEY` in the mode-0600, gitignored local `.env` alongside
`EVOX_BAND_AGENT_ID`, `EVOX_BAND_HUMAN_ID`, and `EVOX_BAND_HUMAN_HANDLE`. The original
`BAND_API_KEY` remains a provisioning-only human credential and must not be supplied to
the agent runtime.

Before registration, the human credential was validated through `/api/v1/me/profile`
and the owned-agent list was checked for an exact-name collision. After registration,
the new agent key was validated through `/api/v1/agent/me`, including an exact match to
the returned agent ID. No duplicate agent existed and no fallback credential or provider
was used.

The REST endpoint returns the agent key only once, so a lost key cannot be recovered from
the registration response later. Runtime or production deployment must copy the four
`EVOX_BAND_*` values into the environment's server-side sponsor secret and must never
ship the human REST key to the application.

Official references:

- [Register external agent](https://docs.band.ai/api/human-api/human-api-agents/register-my-agent)
- [Human API](https://docs.band.ai/api/human-api)
- [Agent API](https://docs.band.ai/api/agent-api)
