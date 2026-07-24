# Evox

Evox is a mission-to-agent-system foundry and governed learning loop built around
[EvoAgentX](https://github.com/EvoAgentX/EvoAgentX). A user defines a problem,
success criteria, evidence, tools, and hard constraints. Evox generates an agent graph,
runs a baseline, evolves candidates on training failures, evaluates them on untouched
cases, and promotes only versions that pass deterministic safety and quality gates.

The hackathon vertical slice resolves real EvoAgentX GitHub issues using official
documentation. The interface exposes five states: **Define**, **System**, **Trial**,
**Gate**, and **Operate**.

## Sponsor architecture

- **Pioneer** is the only production model gateway.
- **Senso** is the cited knowledge/context layer.
- **Actian VectorAI DB** stores searchable run outcomes and failure memory.
- **Band** carries real human escalation and response events.
- **Guild.ai** publishes and governs the promoted resolver.
- **Replay.io** records the browser QA journey and debugging evidence.

These are product capabilities, not logo badges. All adapters fail closed when their
real configuration is absent; production never selects a fake or fallback provider.

## Repository map

```text
packages/api/       FastAPI control plane and workers
packages/web/       Next.js App Router cockpit
infra/terraform/    AWS ECS/SQS/DynamoDB/S3/EFS infrastructure
docs/               Architecture, plan, research, demo and operations
.agents/skills/     Independently runnable $agent-1 ... $agent-16 tasks
evidence/           Truthfully labelled verification manifests
```

## Development contract

Python commands run through `uv`; JavaScript commands run through `pnpm`. The Makefile
is the public entry point. See [MISSION.md](MISSION.md) and
[the implementation plan](docs/plans/2026-07-24-evox-implementation.md).

AWS topology, environment inputs, direct-deploy safety checks, and rollback are documented
in [the deployment runbook](docs/operations/aws-deployment.md).
