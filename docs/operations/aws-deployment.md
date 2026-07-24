# AWS deployment operations

## Production topology

Terraform in `infra/terraform` provisions the Evox application plane in an existing
AWS network:

- CloudFront terminates the public hostname and sends HTTPS traffic to an ALB origin
  hostname. The ALB only accepts traffic from the AWS-managed CloudFront origin prefix
  list.
- ECS Fargate runs separate API, web, and worker services in private subnets. API and
  web accept only ALB traffic; workers have no inbound rule.
- SQS and its encrypted dead-letter queue carry durable jobs. DynamoDB stores durable
  domain state, S3 stores versioned evidence, and encrypted EFS is mounted only by the
  worker through an access point.
- Sponsor credentials come from the two explicitly configured Secrets Manager secrets.
  Terraform reads metadata only; secret values never enter Terraform state.
- CloudWatch receives container logs and reports unhealthy API targets and DLQ messages
  to the configured SNS alarm topic.

The VPC, public and private subnets, outbound NAT or equivalent sponsor connectivity,
Route53 zone, ACM certificates, ECR repositories, SNS alarm topic, and encrypted/versioned
Terraform-state bucket are environment-owned prerequisites. Both ECR repositories must
use immutable tags and scan-on-push. The regional ALB certificate must cover both the
public hostname and `origin.<public-hostname>`; the CloudFront certificate must be in
`us-east-1`.

## Runtime contract

The integrated release must provide all of these interfaces before `make deploy` can
pass:

- API image: listens on port 8000 and returns HTTP 200 from `/healthz` only when required
  persistence and sponsor configuration is usable.
- Worker image: provides the `evox-worker` console entrypoint and consumes
  `EVOX_JOBS_QUEUE_URL` without substituting an in-process queue.
- Web image: a production Next.js build listening on port 3000. The container packages
  only the deployed web workspace and its production dependencies.
- Post-deploy gates: `make verify-live` exercises real sponsor health and `make smoke`
  independently verifies the deployed public journey using `EVOX_BASE_URL`.

The shared runtime variables are `EVOX_AWS_REGION`, `EVOX_DYNAMODB_TABLE`,
`EVOX_EVIDENCE_BUCKET`, and `EVOX_JOBS_QUEUE_URL`. The Pioneer secret must contain a
current `PIONEER_API_KEY`. The sponsor secret must contain non-empty string values for:

- `SENSO_API_KEY`;
- `ACTIAN_VECTORAI_URL`, `ACTIAN_VECTORAI_ACCESS_TOKEN`,
  `EVOX_ACTIAN_OUTCOME_COLLECTION`, and `EVOX_ACTIAN_VECTOR_SIZE`;
- `EVOX_BAND_AGENT_ID`, `EVOX_BAND_API_KEY`, `EVOX_BAND_HUMAN_ID`, and
  `EVOX_BAND_HUMAN_HANDLE`;
- `GUILD_WORKSPACE_ID` and `GUILD_AGENT_ID`.

Missing fields, absent `AWSCURRENT` versions, or missing API/worker/web executables stop
deployment before Terraform changes a service.

## Direct deployment contract

`make deploy` is intentionally non-interactive and fail-closed. It requires:

- `AWS_REGION`, `EVOX_DEPLOY_ENVIRONMENT`, `EVOX_API_IMAGE_REPOSITORY`, and
  `EVOX_WEB_IMAGE_REPOSITORY`;
- `EVOX_TF_STATE_BUCKET` and the environment-specific `EVOX_TF_STATE_KEY`;
- Terraform inputs exported as `TF_VAR_domain_name`, `TF_VAR_certificate_arn`,
  `TF_VAR_cloudfront_certificate_arn`, `TF_VAR_hosted_zone_id`, `TF_VAR_vpc_id`,
  `TF_VAR_public_subnet_ids`, `TF_VAR_private_subnet_ids`,
  `TF_VAR_pioneer_secret_arn`, `TF_VAR_sponsor_secret_arn`, and
  `TF_VAR_alarm_topic_arn`. `TF_VAR_origin_verify_header` is a private random value of at
  least 32 characters used only between CloudFront and the ALB.

Subnet variables use Terraform's JSON list syntax. Values belong in private shell or
credential-manager configuration, never in tracked files.

Before changing AWS, the script verifies the GitHub owner, checked-out `main`, a clean
tree and index, no untracked files, and exact equality with the SHA advertised by
`origin/main`. It runs every local test/build gate, scans repository configuration and
files, builds `linux/amd64` images labelled with the full source SHA, scans them, and
pushes only to verified immutable ECR repositories. Existing SHA images are reused only
when their embedded revision label matches. ECS task definitions use the resolved
registry digest, so tag resolution cannot change a running release.

Terraform uses an encrypted S3 backend with native lock files. ECS deployment circuit
breakers, service-stability waiters, live verification, public smoke checks, and an
ignored local deployment record complete the release. The state bucket must have
versioning, server-side encryption, and all four public-access blocks enabled. On an
update failure, the script restores the three preceding task definitions. On a
first-release failure, it scales all new services to zero. A partial pre-existing service
set is rejected because it cannot be rolled back safely.

The ALB listener denies requests without the private origin header, so another CloudFront
distribution cannot bypass Evox's WAF. Rotate the header without downtime in two applies:
first set the new `TF_VAR_origin_verify_header` and the old value as
`TF_VAR_origin_verify_previous_header`; after CloudFront finishes deploying the new value,
remove the previous value and apply again. Both values are sensitive Terraform inputs and
must come from environment-scoped secret storage. They are retained only in the encrypted,
private Terraform state and temporary plan file, never in source, logs, or deployment
records.

## Verification and rollback

Run `make infra-check` for the non-mutating Terraform, shell, and deploy-contract checks.
No task implementation session should run `make deploy`; deployment is reserved for a
clean, integrated, authorized `main` with real environment configuration.

Deployment records are written with mode 0600 under `evidence/deployments/`. They contain
only revision, environment, endpoint, cluster, immutable image identities, task
definition ARNs, and the rollback instruction. Secret values are never recorded.

If automated rollback cannot restore stability, use the task definition ARNs from the
preceding successful record with `aws ecs update-service`, then wait for all three
services to become stable and rerun independent health and smoke checks. Do not promote
another revision until Terraform refresh shows and reconciles the rollback drift.
