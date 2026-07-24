# Web cockpit decisions — 2026-07-24

## Scope

The cockpit owns the five owner-facing stages: Define, System, Trial, Gate, and
Operate. It is a Next.js App Router application in `packages/web`.

## Decisions

- The Define stage is a client form backed by a server action. The action validates
  the governed mission fields before sending them to the real `POST /v1/missions`
  endpoint.
- `EVOX_API_BASE_URL` is mandatory for control-plane operations. Missing configuration
  returns a specific visible error; it never selects a local, mock, or alternate API.
- Sponsor health is read from `GET /v1/integrations/health`. The strip always names the
  six actual sponsor capabilities and calls missing records `unknown`; it never
  represents them as healthy.
- The remaining stages deliberately show actionable empty states until the control
  plane has persisted a forged graph, candidate evidence, release receipt, or published
  version. No demo mission, graph, score, health result, or release outcome exists in
  production UI code.
- The visual direction is a restrained operational logbook: paper/verdigris palette,
  serif stage statements, and monospaced control-plane metadata. The stage rail is a
  literal sequence through the governed learning loop rather than decorative numbering.

## Trade-offs

The current frozen API fixture publishes endpoint names but not response schemas for
systems, candidates, releases, and operations. The cockpit therefore provides complete
navigation, mission creation, API configuration failure handling, and truthful empty
states now, while avoiding invented contract types. It can render those records once
the corresponding frozen response schemas are published.
