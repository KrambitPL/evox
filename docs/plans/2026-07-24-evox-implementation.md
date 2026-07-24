# Evox implementation plan

Date: 2026-07-24

## Objective

Ship a testable public hackathon system that turns a typed mission into a generated
EvoAgentX workflow, learns from measured failures, gates a candidate on frozen and
held-out evidence, publishes the approved system, and continues collecting production
feedback without self-modifying live.

## Global constraints

1. EvoAgentX `0.1.4` is pinned behind `WorkflowEngine`; never fork it or expose its
   internal graph types as the public contract.
2. Production uses all six real sponsor capabilities: Pioneer, Senso, Actian, Band,
   Guild.ai, and Replay.io. Missing configuration fails closed.
3. No production mocks or provider fallbacks. Test doubles are isolated under tests.
4. Candidate evolution happens offline. Promotion requires frozen evaluation evidence,
   a held-out set, invariant preservation, a versioned receipt, and rollback.
5. Demo corpus uses at least 15 real resolved EvoAgentX issues split 8 train / 4 dev /
   3 held-out. Held-out data is unavailable to optimization.
6. Primary optimizer is SEW and the MVP graph is sequential. Do not add free-form code
   mutation or automatic permission expansion.
7. All long operations return a durable Job. DynamoDB/S3/SQS are production truth.
8. UI has five owner-facing states: Define, System, Trial, Gate, Operate.
9. AWS deployment must use clean remote `main`, immutable SHA artifacts, health gates,
   rollback, and independent smoke verification.

## Frozen public contracts

- `MissionContract`: objective, success criteria, allowed capabilities, hard constraints,
  budgets, evaluation datasets, HITL policy.
- `AgenticSystemSpec`: versioned nodes, edges, models, prompts, capability bindings,
  mutable fields, immutable policy digest.
- `EvaluationCase`: split, input, literal expected facts/disposition/citations, hard gates.
- `RunOutcome`: output, trace/evidence references, score components, cost, latency, status.
- `CandidateReport`: baseline and candidate metrics, repeated results, diffs, invariants.
- `ReleaseDecision`: promote/reject/owner-review, reasons, evidence, version and rollback.
- `Job`: durable queued operation with status, timestamps, result or explicit failure.

## API surface

`POST /v1/missions`; `GET /v1/missions/{id}`; `POST /v1/missions/{id}/forge`;
`POST /v1/systems/{id}/runs`; `POST /v1/systems/{id}/evaluations`;
`POST /v1/systems/{id}/evolutions`; `GET /v1/jobs/{id}`;
`GET /v1/candidates/{id}`; `POST /v1/candidates/{id}/promote`;
`POST /v1/releases/{id}/rollback`; `POST /v1/runs/{id}/feedback`;
`GET /v1/integrations/health`.

## Evaluation proof

The issue resolver score is 35% correct disposition, 35% required facts, 20% citation
quality, and 10% appropriate escalation. Freeze the candidate before held-out testing;
run three repetitions per held-out case. Promotion requires at least +0.05 overall,
no held-out regression, all hard gates passing, and an unchanged immutable digest.

## Execution tasks

1. Foundation: monorepo, frozen schemas, API errors, Makefile, test harness, agent skills.
2. Domain persistence: DynamoDB/S3 repositories, SQS jobs, local contract-test stores.
3. EvoAgentX adapter: graph generation/execution and SEW evolution behind ports.
4. Evaluation: corpus splits, rubric, repeated trials, leakage guard, promotion/rollback.
5. Pioneer: OpenAI-compatible model gateway at `https://api.pioneer.ai/v1`.
6. Senso: ingest/poll/query with citations at the configured Senso API.
7. Actian: vector outcome/failure memory through `actian-vectorai-client`.
8. Band: persistent remote escalation worker and correlated response handling.
9. Guild: versioned resolver publication/control-plane integration.
10. Corpus: fetch, validate, lock, and document 15+ real resolved EvoAgentX issues.
11. Web cockpit: complete Define/System/Trial/Gate/Operate journey and health strip.
12. Infrastructure: Terraform AWS ECS, ALB/CloudFront, SQS, DynamoDB, S3, EFS, secrets.
13. Browser QA: accessibility, Playwright, Replay configuration and journey evidence.
14. Integration: merge task branches, resolve interfaces, run full local gates.
15. Live QA: deploy configured revision, exercise sponsors, fix evidenced defects.
16. Release: final review, truthful evidence report, email, clean push to `main`.

Each task is materialized as `.agents/skills/agent-N/SKILL.md` and may be invoked in a
separate Codex session as `$agent-N` (or selected from `/skills`).

