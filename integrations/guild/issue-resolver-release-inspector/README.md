# Evox Issue Resolver / Release Inspector

This is a Guild runtime agent. Its `agent.ts` uses only the Guild-provided
`@guildai/agents-sdk` and `zod` runtime packages; neither belongs in `package.json`.

The agent inspects evidence and release receipts only. It cannot publish, activate, or
roll back a release. Packaging and publication use `../publish-approved-release.sh`,
which calls the official Guild CLI after Evox has approved an immutable release receipt.

Run `guild agent init` / `guild agent clone` once in this directory to let the official
CLI create and own `guild.json`; do not commit or hand-author that file.
