# Agent 9 handoff — Guild.ai

Date: 2026-07-24

## Delivered

- A typed `PublicationPort` receipt with active version and rollback linkage.
- A fail-closed `GuildPublicationAdapter` that validates promotion authority, remote
  workspace/agent identity, release ID, active version, immutable policy digest, and
  rollback linkage; it supports reconciliation and receipt-linked rollback.
- A Guild-runtime-only Issue Resolver / Release Inspector agent and an official-CLI
  packaging script that requires matching immutable approved release IDs.

## Verification

```text
uv run --package evox-api pytest packages/api/tests  # 26 passed
uv run --package evox-api ruff check packages/api/src packages/api/tests  # passed
bash -n integrations/guild/publish-approved-release.sh  # passed
git diff --check  # passed
```

`guild auth status` reported `Not authenticated`, so no external publication was made.
That is expected fail-closed behavior; configure Guild authentication and workspace/agent
identity before a live release.
