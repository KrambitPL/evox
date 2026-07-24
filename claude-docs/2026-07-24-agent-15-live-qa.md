# Live QA decisions

Live verification remains strictly evidence-based. Presence checks never printed credential
values, and no service was marked healthy without a deployed response. The readiness endpoint
reports only API process readiness; it does not imply sponsor health. Sponsor truth remains at
the separate integration-health endpoint and is enforced by `verify_live.sh`.

The worker executable remains blocked rather than being satisfied with an empty dispatcher or
synthetic job behavior. Existing durable jobs do not persist the operation input needed to
reconstruct real work after SQS delivery, so a truthful worker requires a reviewed contract and
composition change.
