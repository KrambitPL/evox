# Browser QA and Replay access

The browser suite exercises real Evox deployments. It never intercepts API requests,
injects browser-side sponsor responses, or substitutes a local fixture. Run it only
against designated, configured test deployments: one healthy deployment and one whose
named sponsor is deliberately unconfigured so that the server returns its real
fail-closed state.

## Required environment

```zsh
export EVOX_E2E_BASE_URL='https://evox-test.example'
export EVOX_E2E_FAIL_CLOSED_BASE_URL='https://evox-sponsor-unavailable.example'
export EVOX_E2E_UNAVAILABLE_SPONSOR='Senso'
```

`EVOX_E2E_BASE_URL` must serve the complete, healthy cockpit. The browser suite creates
and advances an actual isolated test mission, polls actual durable jobs, promotes only
when the configured candidate is eligible, and rolls it back. Do not point these values
at a customer environment. The fail-closed URL must be a separate real environment with
the selected integration absent from server-side configuration; it is not a simulated
HTTP response.

Run the non-recording checks with:

```zsh
make e2e
```

The suite expects the cockpit to provide semantic landmarks, an `Owner workflow`
navigation region, five named workflow links, labeled mission fields, live `status`
messages for each queued/polled job, and an `alert` for validation and unavailable
sponsor states. Those are product accessibility requirements, not test-only markup.

## Replay setup and upload

1. Create or select the Evox Replay Test Suite workspace, grant access only to the
   engineering group, and create a test-suite API key.
2. Store that key as `REPLAY_API_KEY` in the CI/deployment secret store. Never put it in
   `.env.example`, the browser bundle, command output, screenshots, or evidence.
3. Install the Replay browser after workspace dependencies are installed:

   ```zsh
   pnpm exec replayio install
   ```

4. Authorize an upload explicitly and run the Replay project:

   ```zsh
   export EVOX_REPLAY_UPLOAD=true
   make test-replay
   ```

The configuration uses `@replayio/playwright`, the `replay-chromium` project and
`replayReporter` with upload enabled only when `EVOX_REPLAY_UPLOAD=true`. This keeps
ordinary local browser runs from uploading. Replay recordings are private by default;
keep their workspace private and do not share recording links outside the approved team.

Replay records browser and network activity, so the designated QA deployments must use
non-personal, non-secret test state. The tests never type a credential. Failure
screenshots mask controls whose accessible labels identify access tokens, API keys,
secrets, or feedback. Do not add customer content or credentials to a Replay scenario.

## Expected verification

`make e2e` covers keyboard navigation, landmarks and roles, mobile layout, API error
announcements, the full Define → System → Trial → Gate → Operate → rollback flow, job
polling, and a genuine unavailable-sponsor state. `make test-replay` repeats that suite
in Replay Chromium and uploads the recordings only with the explicit opt-in above.
