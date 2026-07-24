# Evox mission

## The user's definition, preserved verbatim

> so shouldnt we build an app that is quite generic i.e. not business specific. I.e. human gives a problem statement success criteria anything else we need, then we generate the multi agent system with the graph and the models and then if there are test data it self-evolves to solve the system according to the problem. Afterwards you can start using the solution and it evolves on any failures and reinforces on successes i.e. you can either load it up with existing labeled data or have clear success criteria or use HITL. Store this verbatim first. Is this what you expected?

## Product mission

Evox turns a measurable problem into a governed, versioned agentic system. It uses
EvoAgentX to generate, execute, evaluate, and evolve candidate workflows. Evox owns
the parts a production operator needs around that engine: a typed mission contract,
immutable authority boundaries, frozen evaluation data, held-out release gates,
human escalation, auditable promotion receipts, monitoring, and rollback.

The core promise is deliberately precise:

> EvoAgentX evolves candidate workflows. Evox decides whether they earned authority.

The first proof is an EvoAgentX issue resolver grounded in official documentation and
real resolved GitHub issues. It must show that a candidate beats the active version on
frozen evidence, without expanding permissions or changing the evaluator.

