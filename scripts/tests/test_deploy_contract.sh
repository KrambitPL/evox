#!/usr/bin/env bash
# Test-specific exports are intentionally isolated by subshell test functions.
# shellcheck disable=SC2030,SC2031
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
grep -q 'EVOX_CONTAINER_PLATFORM' "$deploy_script"
grep -q 'variable "cpu_architecture"' "$root_dir/infra/terraform/variables.tf"
grep -q 'kms_key_id.*aws_kms_key.durable' "$root_dir/infra/terraform/main.tf"
grep -q 'safe first-deployment resume rejects active partial ECS services' "$deploy_script"

test_verify_release_stops_on_failed_gate() (
  local deploy_library marker release_output release_status
  deploy_library=$(mktemp "$root_dir/scripts/deploy-library.XXXXXX")
  marker=$(mktemp "${TMPDIR:-/tmp}/evox-late-gate.XXXXXX")
  /bin/rm -f "$marker"
  trap '/bin/rm -f "$deploy_library" "$marker"' EXIT
  sed '$d' "$deploy_script" >"$deploy_library"

  export AWS_REGION=test-region-1
  export EVOX_API_IMAGE_REPOSITORY=registry.test/evox-api
  export EVOX_WEB_IMAGE_REPOSITORY=registry.test/evox-web
  export EVOX_TF_STATE_BUCKET=evox-test-state
  export EVOX_TF_STATE_KEY=production/terraform.tfstate
  export EVOX_ALLOW_UNAVAILABLE_SPONSORS=true
  export EVOX_REPLAY_UPLOAD=false
  # shellcheck source=/dev/null
  source "$deploy_library"
  # Assigned by the sourced deploy script.
  # shellcheck disable=SC2154
  test "$TF_VAR_available_sponsors" = '["senso"]'

  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  terraform() { printf 'https://evox.example.test\n'; }
  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  curl() { return 0; }
  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  make() {
    if test "${1:-}" = "verify-live"; then
      return 23
    fi
    touch "$marker"
  }
  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  pnpm() { touch "$marker"; }

  set +e
  release_output=$(verify_release 2>/dev/null)
  release_status=$?
  set -e

  test "$release_status" -eq 23
  test -z "$release_output"
  test ! -e "$marker"
)

test_verify_release_stops_on_failed_gate

test_image_build_disables_unscannable_oci_index() (
  local build_args deploy_library revision
  deploy_library=$(mktemp "$root_dir/scripts/deploy-library.XXXXXX")
  build_args=$(mktemp "${TMPDIR:-/tmp}/evox-build-args.XXXXXX")
  revision=0000000000000000000000000000000000000000
  trap '/bin/rm -f "$deploy_library" "$build_args"' EXIT
  sed '$d' "$deploy_script" >"$deploy_library"

  export AWS_REGION=test-region-1
  export EVOX_API_IMAGE_REPOSITORY=registry.test/evox-api
  export EVOX_WEB_IMAGE_REPOSITORY=registry.test/evox-web
  export EVOX_TF_STATE_BUCKET=evox-test-state
  export EVOX_TF_STATE_KEY=production/terraform.tfstate
  export EVOX_ALLOW_UNAVAILABLE_SPONSORS=true
  # shellcheck source=/dev/null
  source "$deploy_library"

  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  image_exists() { return 1; }
  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  docker() {
    case "${1:-} ${2:-}" in
      'buildx build') printf '%s\n' "$*" >"$build_args" ;;
      'image inspect') printf '%s\n' "$revision" ;;
      *) return 0 ;;
    esac
  }
  # Invoked indirectly by the sourced deploy function.
  # shellcheck disable=SC2329
  trivy() { return 0; }

  build_or_reuse_image registry.test/evox-web Dockerfile.web "$revision"
  grep -q -- '--provenance=false' "$build_args"
)

test_image_build_disables_unscannable_oci_index

test_partial_live_policy_allows_missing_optional_auth() (
  local fake_bin output
  fake_bin=$(mktemp -d "${TMPDIR:-/tmp}/evox-live-policy.XXXXXX")
  trap '/bin/rm -rf "$fake_bin"' EXIT
  cat >"$fake_bin/curl" <<'EOF'
#!/usr/bin/env bash
case "${*: -1}" in
  */healthz) printf '{"status":"ready"}\n' ;;
  */v1/integrations/health)
    printf '%s\n' '{"services":[{"name":"Pioneer","status":"healthy"},{"name":"Senso","status":"healthy"},{"name":"Actian","status":"unavailable"},{"name":"Band","status":"unavailable"},{"name":"Guild.ai","status":"unavailable"},{"name":"Replay.io","status":"unavailable"}]}'
    ;;
  *) exit 1 ;;
esac
EOF
  chmod +x "$fake_bin/curl"

  output=$(
    PATH="$fake_bin:$PATH" \
      EVOX_BASE_URL=https://evox.example.test \
      EVOX_ALLOW_UNAVAILABLE_SPONSORS=true \
      "$root_dir/scripts/verify_live.sh"
  )
  grep -q 'configured integration policy passed' <<<"$output"
)

test_partial_live_policy_allows_missing_optional_auth

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
