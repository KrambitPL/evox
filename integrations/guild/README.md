# Guild.ai integration

`issue-resolver-release-inspector/` is the only directory that imports
`@guildai/agents-sdk`, and Guild provides that SDK only in its supported agent runtime.
The package intentionally declares no SDK dependency.

Use `publish-approved-release.sh` from the initialized Guild agent directory. It requires
the workspace identity and an Evox-approved immutable release ID, checks the CLI's
credential state without handling credentials itself, waits for validation, publishes,
and reads the active/version history for reconciliation. Missing configuration or a
release mismatch fails closed.
