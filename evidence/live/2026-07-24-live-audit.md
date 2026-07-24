# Live audit

Timestamp: 2026-07-24T21:44:25Z

## Credential and environment audit

- GitHub authentication: configured for the authorized `KramPiotr` account.
- AWS authentication: configured; account and principal identifiers redacted.
- GitHub repository secrets: 0 names configured.
- GitHub repository variables: 0 names configured.
- Configured AWS region: present.
- Evox AWS Secrets Manager entries: 0.
- Evox ECR repositories: 0.
- Evox ECS clusters: 0.
- Local `.env`: Pioneer, Senso, Band, and Replay authentication keys are present. Values
  were sourced only for the authorized deploy attempt and were never printed.
- Actian/Guild credentials, Band identity fields, AWS deployment resource inputs, and
  deployed endpoint variables: absent.

## Deployment attempt

`make deploy` was invoked through the reviewed deployment entry point. It failed closed at
2026-07-24T21:41Z because `AWS_REGION` was not exported for the deployment contract. No AWS,
registry, DNS, GitHub, or public endpoint mutation occurred.

After authorization to use `.env`, it was invoked again at 2026-07-24T21:47Z with the
configured AWS region and local authentication keys. It failed closed because
`EVOX_API_IMAGE_REPOSITORY` is not configured. No mutation occurred.

## Live exercise matrix

| Lane | Result | Concrete blocker |
| --- | --- | --- |
| Pioneer | blocked | local key present, but no deployed endpoint |
| Senso | blocked | local key present, but no deployed endpoint |
| Actian | blocked | no deployed endpoint or configured credential |
| Band roundtrip | blocked | no deployed endpoint or configured agent/human credentials |
| Guild publication | blocked | no deployed endpoint, authentication, workspace, or agent ID |
| Replay recording | blocked | local key present, but no upload authorization or browser endpoint |
| API lifecycle | blocked | no deployment; production dependency injection remains incomplete |
| Browser journey | blocked | `EVOX_E2E_BASE_URL` and fail-closed environment are absent |
| Independent smoke | blocked | `EVOX_BASE_URL` is absent |

No live sponsor call, publication, Replay upload, or customer-facing release was claimed.
