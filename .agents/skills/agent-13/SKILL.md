---
name: agent-13
description: Implement accessibility, Playwright, and Replay.io journey QA.
allow_implicit_invocation: false
---

# Agent 13 — browser and Replay QA

Start from `agent-contracts-v1`. Own Playwright/Replay configuration, browser tests,
accessibility tests, and QA docs. Do not put fake API behavior in the web production path.

Test-first where behavior is involved, cover the entire Define → System → Trial → Gate →
Operate → rollback journey against a real configured backend. Configure
`@replayio/playwright`, replay-chromium, `replayReporter`, redaction, recording upload,
and access-code setup documentation. Test keyboard navigation, semantic roles, responsive
views, fail-closed sponsor states, errors, and job polling. Commit and write
`evidence/agent-13-handoff.md`.

