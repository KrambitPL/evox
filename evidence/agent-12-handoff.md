# Agent 12 handoff — AWS and deployment

Date: 2026-07-24
Branch: `agent-12/aws-deployment`
Base: `agent-contracts-v1`

## Delivered

- Terraform for CloudFront/WAF, Route53, HTTPS ALB, private ECS Fargate API/web/worker
  services, SQS with DLQ, DynamoDB, KMS-encrypted/versioned S3, encrypted/backup-enabled
  EFS, Secrets Manager references, least-privilege IAM, CloudWatch logs/alarms, and
  operational outputs.
- Non-root multi-stage API and Next.js production web images with source revision labels,
  restricted build context, read-only ECS roots, and `linux/amd64` release builds.
- `make deploy` implementation enforcing authorized GitHub ownership, clean exact remote
  `main` before and after full local gates, real current secrets, immutable/scanned ECR,
  source-labelled SHA images, digest-pinned task definitions, locked remote Terraform
  state, readiness, real live verification, independent smoke, deployment records, and
  rollback.
- Deployment and integration runbook in `docs/operations/aws-deployment.md`.

## Verified

- `make infra-check`: Terraform formatting, offline initialization, `terraform validate`,
  ShellCheck, and the deploy fail-closed contract all pass.
- `make test-unit`: 18 passed.
- `make test-contract`: 18 passed.
- `make lint`: passed.
- `trivy config --exit-code 1 --severity HIGH,CRITICAL .`: zero findings. The two public
  HTTPS egress rules and internet-facing CloudFront origin ALB have narrow, documented
  suppressions; origin ingress is restricted to the AWS-managed CloudFront prefix list.
- `trivy filesystem --exit-code 1 --scanners vuln,secret --severity HIGH,CRITICAL .`:
  no secrets detected; application dependency vulnerabilities are enforced again on the
  built images.
- The API image built successfully for `linux/amd64` on Colima, runs as UID 10001, carries
  the exact source revision label, starts Uvicorn 0.34.0, and has zero actionable high or
  critical findings under the release scan (`--ignore-unfixed`).

## Integration dependencies

- Agent 11's committed `packages/web` and web build gate must be integrated before the
  web image can be built. They are intentionally not copied into this isolated task branch.
- The web Dockerfile was built successfully against Agent 14's integrated tree on the
  native `linux/arm64` verification platform; the container booted as UID 10001, reached
  Next.js readiness, and served `/` successfully. Its current integrated lock contains
  actionable `postcss` and `sharp` production dependency vulnerabilities, so the release
  scan correctly blocks publication until the web dependency lane updates and verifies
  that lock.
- The integrated API must implement a truthful `/healthz` and package an `evox-worker`
  console entrypoint. The deploy preflight rejects an image missing that real worker
  executable; no fallback is present.
- Agent 15 must implement `make verify-live` and `make smoke` against `EVOX_BASE_URL`.
- Environment owners must supply the reviewed VPC/subnets, DNS/certificates, immutable
  scan-on-push ECR repositories, state bucket, SNS alarm topic, and current Secrets Manager
  values described by the runbook.

No AWS infrastructure, image registry, DNS, secret, or public endpoint was changed during
this task. `make deploy` was not run.
