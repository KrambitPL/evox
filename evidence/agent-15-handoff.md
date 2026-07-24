# Agent 15 handoff — live QA

Date: 2026-07-24

## Fixed defects

- Added the ALB/ECS-required `/healthz` process readiness route after a failing integration
  regression demonstrated the deployed contract returned 404.
- Replaced the placeholder integration Make target with the real integration suite.
- Replaced placeholder `verify-live` and `smoke` targets with executable, fail-closed HTTPS
  probes. The live verifier requires readiness plus healthy Pioneer, Senso, Actian, Band,
  Guild, and Replay statuses; smoke independently checks API readiness and the web endpoint.
- Extended the deployment contract test to require the live verification scripts.

## Local verification

- `make test-integration` — 1 passed
- `make test-unit` — 70 passed
- `make test-contract` — 24 passed
- `make lint` — passed
- Web unit tests — 4 passed
- Web lint and production build — passed
- `make infra-check` — passed

## Live outcome

Deployment and all live lanes are blocked by absent AWS deployment resource inputs,
Actian/Guild credentials, Band identity fields, and endpoints. Pioneer, Senso, Band, and
Replay keys were sourced from the local `.env` without printing them. The reviewed
`make deploy` failed before mutation because no API ECR repository URI is configured. Full
redacted evidence is in `evidence/live/2026-07-24-live-audit.md`.

The API image also lacks the required `evox-worker` executable. This was not patched with an
empty handler registry: the durable `Job` contract contains no operation payload with which a
real worker can reconstruct forge/run/evaluate/evolve/promote/rollback work. Resolving it
requires an application-composition contract change, not a live-QA fallback.
