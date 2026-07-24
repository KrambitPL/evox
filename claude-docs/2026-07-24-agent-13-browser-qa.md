# Agent 13 browser QA decisions — 2026-07-24

- Browser QA targets externally configured Evox deployments rather than starting a
  web server or intercepting API traffic. This keeps the browser journey on the real
  backend and makes missing configuration explicit.
- The healthy journey and unavailable-sponsor scenario have distinct base URLs. A
  separate real environment must lack the named sponsor configuration, so the
  fail-closed assertion cannot be produced by a browser stub.
- Replay uploads require both `REPLAY_API_KEY` and the explicit
  `EVOX_REPLAY_UPLOAD=true` opt-in. Ordinary Chromium runs never upload recordings.
- Replay captures browser/network activity. The suite uses only designated no-PII test
  state, never types credentials, and masks potentially sensitive controls in saved
  failure screenshots.
- The accessibility contract is deliberately semantic: owner-workflow navigation,
  landmarks, native controls, labelled inputs, `status` job updates and `alert` error
  announcements. The cockpit must provide these as product behavior.
