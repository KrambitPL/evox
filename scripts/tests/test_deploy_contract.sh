#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
deploy_script="$root_dir/scripts/deploy.sh"

test -x "$deploy_script"
grep -Eq 'KrambitPL|KramPiotr' "$deploy_script"
grep -q 'diff --quiet' "$deploy_script"
grep -q 'ls-remote --exit-code origin refs/heads/main' "$deploy_script"
grep -Fq "verified_revision=\$(verify_release_authority)" "$deploy_script"
grep -Fq "test \"\$verified_revision\" = \"\$revision\"" "$deploy_script"
grep -q 'ROLLBACK' "$deploy_script"
grep -q 'deployment-record' "$deploy_script"
grep -q 'imageTagMutability' "$deploy_script"
grep -q 'scan-on-push' "$deploy_script"
grep -q 'get-secret-value' "$deploy_script"
grep -q 'get-bucket-encryption' "$deploy_script"
grep -q 'describe-clusters' "$deploy_script"
grep -q 'command -v evox-worker' "$deploy_script"
test -x "$root_dir/scripts/verify_live.sh"
test -x "$root_dir/scripts/smoke.sh"
grep -q 'scripts/verify_live.sh' "$root_dir/Makefile"
grep -q 'scripts/smoke.sh' "$root_dir/Makefile"
grep -q 'ACTIAN_VECTORAI_ACCESS_TOKEN' "$deploy_script"
grep -q 'EVOX_BAND_AGENT_ID' "$deploy_script"
grep -q 'GUILD_WORKSPACE_ID' "$deploy_script"
grep -q 'make verify-live' "$deploy_script"
grep -q 'make smoke' "$deploy_script"
grep -q 'EVOX_ALLOW_UNAVAILABLE_SPONSORS' "$deploy_script"
grep -q 'test:e2e:partial' "$deploy_script"
grep -q 'TF_VAR_available_sponsors' "$deploy_script"
grep -q 'TF_VAR_manage_route53' "$deploy_script"
grep -q 'HOSTIDO_DNS_PROJECT' "$deploy_script"
grep -q 'variable "available_sponsors"' "$root_dir/infra/terraform/variables.tf"
grep -q 'variable "manage_route53"' "$root_dir/infra/terraform/variables.tf"
grep -q 'variable "assign_public_ip"' "$root_dir/infra/terraform/variables.tf"
grep -q 'REPLAY_API_KEY' "$root_dir/infra/terraform/compute.tf"
grep -q 'EVOX_API_BASE_URL' "$root_dir/infra/terraform/compute.tf"

set +e
output=$(
  AWS_REGION=eu-central-1 \
  EVOX_API_IMAGE_REPOSITORY=000000000000.dkr.ecr.eu-central-1.amazonaws.com/evox-api \
  EVOX_WEB_IMAGE_REPOSITORY=000000000000.dkr.ecr.eu-central-1.amazonaws.com/evox-web \
  EVOX_TF_STATE_BUCKET=evox-state \
  EVOX_TF_STATE_KEY=production/terraform.tfstate \
  TF_VAR_domain_name=evox.example.test \
  TF_VAR_certificate_arn=arn:aws:acm:eu-central-1:000000000000:certificate/test \
  TF_VAR_cloudfront_certificate_arn=arn:aws:acm:us-east-1:000000000000:certificate/test \
  TF_VAR_hosted_zone_id=TEST \
  TF_VAR_vpc_id=vpc-test \
  TF_VAR_public_subnet_ids='["subnet-a","subnet-b"]' \
  TF_VAR_private_subnet_ids='["subnet-c","subnet-d"]' \
  TF_VAR_pioneer_secret_arn=arn:aws:secretsmanager:eu-central-1:000000000000:secret:pioneer \
  TF_VAR_sponsor_secret_arn=arn:aws:secretsmanager:eu-central-1:000000000000:secret:sponsors \
  TF_VAR_alarm_topic_arn=arn:aws:sns:eu-central-1:000000000000:evox-alarms \
  TF_VAR_origin_verify_header=test-only-origin-header-000000000 \
  "$deploy_script" 2>&1
)
status=$?
set -e

test "$status" -ne 0
grep -q 'deployment requires checked-out main' <<<"$output"
