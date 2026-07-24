# Architecture and sponsor rationale

EvoAgentX already provides workflow generation, action execution, evaluators, and
optimizers including SEW. Evox does not duplicate those features. It wraps them with a
stable application contract and adds the production learning loop: durable jobs,
evidence ownership, immutable authority, train/dev/held-out isolation, promotion,
operation, feedback, and rollback.

| Capability | Owner | Adds or replaces |
|---|---|---|
| Workflow generation/execution/evolution | EvoAgentX adapter | Existing engine capability |
| Model inference/routing | Pioneer | Replaces only EvoAgentX's direct model provider |
| Cited official knowledge | Senso | Adds governed retrieval; replaces local demo RAG |
| Outcome/failure similarity memory | Actian | Adds durable evolutionary memory |
| Human escalation | Band | Adds remote, correlated HITL coordination |
| Published active agent and governance | Guild.ai | Adds outer deployment/control plane |
| Browser QA evidence | Replay.io | Adds deterministic product QA and debugging |
| Mission, gate, releases, rollback | Evox | New product layer |

Durable product code depends on `WorkflowEngine`, `ModelGateway`, `KnowledgePort`,
`OutcomeMemoryPort`, `EscalationPort`, `PublicationPort`, and `QaEvidencePort`.
Only adapters know SDK or wire formats. This limits lock-in to a single EvoAgentX or
sponsor release.

Comparable projects include AutoGen Studio, LangGraph/LangSmith, and low-code agent
builders. They compose, observe, or deploy workflows. Evox's release unit is the owner's
typed mission plus its authority boundary and evidence gate.

