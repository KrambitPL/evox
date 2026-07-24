# Agent 11 handoff — web cockpit

Date: 2026-07-24

## Delivered

- New Next.js App Router cockpit at `packages/web`.
- Responsive Define, System, Trial, Gate, and Operate stage navigation.
- Governed mission capture for objective, criteria, capabilities, constraints,
  datasets, budget, and human approval requirement.
- Real server-side control-plane client for mission creation and sponsor health.
- Truthful six-sponsor health strip and accessible validation, error, and empty states.
- Unit tests for mission validation and health normalization.

## Verification

```text
pnpm --filter @evox/web test   # 4 passed
pnpm --filter @evox/web lint   # passed
pnpm --filter @evox/web build  # passed
```

## Integration notes

- Configure `EVOX_API_BASE_URL` in server-side environment storage before using live
  mutations or health reads.
- The frozen endpoint manifest has no response schemas for graph, candidate, release,
  or operations records. The UI intentionally exposes explicit empty states instead of
  fabricating those results. Add renderers only against the later frozen response types.
- Replay-specific e2e setup remains owned by Agent 13.
