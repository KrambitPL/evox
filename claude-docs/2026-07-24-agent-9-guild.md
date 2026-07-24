# Guild publication governance — 2026-07-24

## Decision

Evox treats `ReleaseDecision` as the sole approval authority for Guild publication.
`GuildPublicationAdapter` validates the promoted system and immutable policy digest before
calling the injected official-CLI boundary, then rejects remote state unless workspace,
agent, release ID, version, immutable digest, and rollback linkage all agree.

## Trade-offs

- Guild's credential store and the official CLI remain the only credential path. The API
  adapter accepts no token, API key, or undocumented HTTP endpoint.
- `PublicationReceipt` lives at the port boundary, so application code gets a typed active
  version/rollback result without importing a Guild adapter.
- The Guild runtime agent is inspection-only. It uses the SDK exclusively in `agent.ts`;
  packaging runs through the official CLI script, so the agent cannot mutate release state.

## Verification

`uv run --package evox-api pytest packages/api/tests`, Ruff, shell syntax checking, and
`git diff --check` all passed locally. Guild authentication was absent in this environment,
and `guild auth status` failed closed; no live publication was attempted.
