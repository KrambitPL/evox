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
Replay recording is optional and runs only when a valid local key and explicit upload
authorization are both present. Replay, Actian, Band, and Guild.ai may report
`unavailable` (or an explicitly allowed degraded status) instead of receiving empty
secret values, synthetic behavior, or fallback providers. The manual deployment does
not require local `.env` authentication keys.

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
BuildKit provenance attestations are disabled for these ECR artifacts so each tag is
a single scannable image manifest rather than an OCI image index unsupported by ECR's
basic scanner. Source revision labels and immutable digest identity remain enforced.

The deploy fails closed on source authority, dirty worktrees, missing mandatory
secrets, mutable or unscanned ECR repositories, unsafe state storage, local tests,
lint, builds, HIGH/CRITICAL source or image findings, ECS readiness, live health,
smoke tests, and browser QA. First-release rollback scales the newly created services
to zero; later releases restore the preceding task definitions. Release verification
uses an explicit fail-fast command chain so a failed live or browser gate cannot be
masked by Bash command-substitution behavior.

The owner cockpit is rendered dynamically at runtime. This is required because the
API URL is a server-side runtime setting rather than a build argument; static
prerendering would permanently bake an empty integration-health state into the image.
