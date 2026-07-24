# Agent 13 handoff — browser, accessibility, and Replay QA

Date: 2026-07-24

## Delivered

- Added the `@evox/web` Playwright workspace with pinned `@playwright/test` and
  `@replayio/playwright` dependencies.
- Configured stock Chromium and `replay-chromium`; `replayReporter` uploads only when
  `EVOX_REPLAY_UPLOAD=true` and a Replay API key is present.
- Added no-stub browser coverage for the complete Define → System → Trial → Gate →
  Operate → rollback lifecycle, durable-job polling, keyboard navigation, semantic
  roles, validation errors, responsive layout, and a real unavailable-sponsor
  environment.
- Added masked failure screenshots and the Replay access/redaction runbook at
  `docs/operations/replay-browser-qa.md`.
- Connected `make e2e` and `make test-replay` to the workspace. `test-replay` fails
  before execution unless upload is explicitly authorized and keyed.

## UI integration contract for Agent 11 / Agent 14

The cockpit must expose a banner, main landmark, `Owner workflow` navigation with five
links (Define, System, Trial, Gate, Operate), labelled objective/success criteria/hard
constraint inputs, named action buttons, job `status` regions, and `alert` regions for
validation and unavailable integrations. These are required product accessibility
semantics.

## Verification

| Check | Result |
| --- | --- |
| Failing test-first invocation before workspace existed | observed: `No projects matched the filters` |
| `pnpm install --frozen-lockfile` | passed |
| `EVOX_E2E_BASE_URL=http://127.0.0.1:3000 pnpm --filter @evox/web exec playwright test --list --project=chromium` | passed; 5 tests discovered |
| Missing `EVOX_E2E_BASE_URL` guard | passed; configuration fails closed with the required-variable error |
| Full `make e2e` | not run: no configured healthy and unavailable-sponsor Evox deployment was supplied |
| Replay upload | not run: no `REPLAY_API_KEY` or explicit upload authorization was supplied |

## Required live environment

Set `EVOX_E2E_BASE_URL`, `EVOX_E2E_FAIL_CLOSED_BASE_URL`, and
`EVOX_E2E_UNAVAILABLE_SPONSOR` as documented in the runbook. For recording, also set
the server-side secret-derived `REPLAY_API_KEY` in the runner environment and explicitly
set `EVOX_REPLAY_UPLOAD=true`; install the Replay browser with `pnpm exec replayio install`.
