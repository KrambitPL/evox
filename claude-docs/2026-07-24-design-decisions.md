# Design decisions — 2026-07-24

- The repository and product are named Evox; GORGOS remains the broader organizational
  mission/control-plane direction.
- The hackathon delivers a generic contract through one narrow, falsifiable issue-
  resolver proof rather than claiming arbitrary-mission production readiness.
- EvoAgentX is pinned and adapted, not forked. Evox owns governance and versioning.
- All six sponsors have real fail-closed boundaries. Logos without live evidence do not
  count as integration.
- Pioneer, not CLIProxyAPI, is the explicit production model route for this repository.
- Live systems never self-edit. Failures enqueue an offline candidate cycle.
- Held-out cases are sealed from optimizers and only opened after candidate freeze.
- Infrastructure targets AWS, while local tests use isolated test doubles only.

