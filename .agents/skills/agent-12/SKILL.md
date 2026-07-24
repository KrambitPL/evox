---
name: agent-12
description: Implement AWS Terraform, container builds, operations, and safe direct deploy.
allow_implicit_invocation: false
---

# Agent 12 — AWS and deployment

Start from `agent-contracts-v1`. Own `infra/`, Dockerfiles, deployment scripts, deployment
Make targets, and ops docs. Do not deploy or expose secrets while implementing. Coordinate
with concurrent agents through documented interfaces.

Build least-privilege Terraform for ECS Fargate API/web/workers, ALB/CloudFront, SQS with
DLQ, DynamoDB, S3, EFS where EvoAgentX needs durable files, Secrets Manager, logs, alarms,
and outputs. `make deploy` must verify owner KrambitPL/KramPiotr, clean tree, exact remote
main SHA, immutable SHA images, local tests/scans, readiness, smoke, deployment record,
and rollback; fail closed if equivalence cannot be met. Commit and write
`evidence/agent-12-handoff.md`.

