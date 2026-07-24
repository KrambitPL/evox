# Manual partial-integration deployment decision

Date: 2026-07-24

## Decision

Evox production deployment uses the repository's reviewed `make deploy` path from a
clean checkout of the exact SHA on the authorized `KrambitPL/evox` remote `main`.
GitHub Actions is not part of this release path.

The initial deployment uses `evox.aident.pl`, the existing `*.aident.pl` ACM
certificate, AWS ECS/Fargate, ECR, CloudFront, WAF, DynamoDB, SQS, EFS, and S3.
Authoritative DNS remains in Hostido, so Terraform publishes infrastructure outputs
and the deployment script updates the exact `evox` and `origin-evox` CNAME records
through the configured `hostido-dns` integration.

## Integration contract

The user explicitly authorized deployment without every sponsor credential. The
release therefore sets `EVOX_ALLOW_UNAVAILABLE_SPONSORS=true` and injects only secret
fields for configured integrations. Pioneer and Senso remain mandatory live gates.
Replay is configured for browser evidence. Actian, Band, and Guild.ai must report
`unavailable` (or an explicitly allowed degraded publication status for Guild.ai)
instead of receiving empty secret values, synthetic behavior, or fallback providers.

Pioneer remains the only model gateway. This decision does not introduce
CLIProxyAPI, OpenAI, Azure, or any other fallback route.

## Operational tradeoffs

The available account supplies a default VPC and public subnets but no private NAT
network. The release explicitly assigns public IPs to Fargate tasks so configured
sponsor APIs and AWS endpoints are reachable. Task security groups expose no direct
inbound access; application traffic still arrives only through the CloudFront-restricted
ALB. A later network-hardening release can replace this with private subnets, NAT, and
VPC endpoints without changing application contracts.

The release publishes native `linux/arm64` images and declares matching `ARM64`
Fargate runtime platforms. The deploy contract validates that image and task
architectures agree; this avoids unreliable cross-architecture emulation on the
ARM64 release host while preserving immutable digests and the same security gates.

The deploy fails closed on source authority, dirty worktrees, missing mandatory
secrets, mutable or unscanned ECR repositories, unsafe state storage, local tests,
lint, builds, HIGH/CRITICAL source or image findings, ECS readiness, live health,
smoke tests, and browser QA. First-release rollback scales the newly created services
to zero; later releases restore the preceding task definitions.
