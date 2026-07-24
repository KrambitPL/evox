#!/usr/bin/env bash
set -euo pipefail

root_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
readonly root_dir
if test -f "$root_dir/.env"; then
  set -a
  # shellcheck source=/dev/null
  source "$root_dir/.env"
  set +a
fi
readonly terraform_dir="$root_dir/infra/terraform"
readonly environment=${EVOX_DEPLOY_ENVIRONMENT:-production}
readonly allow_unavailable_sponsors=${EVOX_ALLOW_UNAVAILABLE_SPONSORS:-false}
if test "$allow_unavailable_sponsors" = "true"; then
  export TF_VAR_available_sponsors=${TF_VAR_available_sponsors:-'["senso"]'}
else
  export TF_VAR_available_sponsors=${TF_VAR_available_sponsors:-'["senso","actian","band","guild","replay"]'}
fi
export TF_VAR_manage_route53=${TF_VAR_manage_route53:-true}
export TF_VAR_assign_public_ip=${TF_VAR_assign_public_ip:-false}
readonly manage_route53=$TF_VAR_manage_route53
readonly container_platform=${EVOX_CONTAINER_PLATFORM:-linux/amd64}
case "$container_platform" in
  linux/amd64) export TF_VAR_cpu_architecture=${TF_VAR_cpu_architecture:-X86_64} ;;
  linux/arm64) export TF_VAR_cpu_architecture=${TF_VAR_cpu_architecture:-ARM64} ;;
  *) printf 'deploy: unsupported EVOX_CONTAINER_PLATFORM: %s\n' "$container_platform" >&2; exit 1 ;;
esac
readonly aws_region=${AWS_REGION:?Set AWS_REGION to the approved deployment region.}
readonly api_repository=${EVOX_API_IMAGE_REPOSITORY:?Set EVOX_API_IMAGE_REPOSITORY to the ECR API repository URI.}
readonly web_repository=${EVOX_WEB_IMAGE_REPOSITORY:?Set EVOX_WEB_IMAGE_REPOSITORY to the ECR web repository URI.}
readonly state_bucket=${EVOX_TF_STATE_BUCKET:?Set EVOX_TF_STATE_BUCKET to the encrypted Terraform state bucket.}
readonly state_key=${EVOX_TF_STATE_KEY:?Set EVOX_TF_STATE_KEY to the environment-specific Terraform state key.}
readonly pioneer_secret_arn=${TF_VAR_pioneer_secret_arn:-}
readonly sponsor_secret_arn=${TF_VAR_sponsor_secret_arn:-}

fail() {
  printf 'deploy: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "required command is unavailable: $1"
}

require_variable() {
  test -n "${!1:-}" || fail "required environment variable is unavailable: $1"
}

verify_release_authority() {
  local push_url local_sha remote_sha
  push_url=$(git -C "$root_dir" remote get-url --push origin)
  case "$push_url" in
    git@github.com:KrambitPL/*|https://github.com/KrambitPL/*|ssh://git@github.com/KrambitPL/*|git@github.com:KramPiotr/*|https://github.com/KramPiotr/*|ssh://git@github.com/KramPiotr/*) ;;
    *) fail "origin owner is not an authorized KrambitPL or KramPiotr repository" ;;
  esac

  test "$(git -C "$root_dir" branch --show-current)" = "main" || fail "deployment requires checked-out main"
  git -C "$root_dir" diff --quiet || fail "deployment requires a clean worktree"
  git -C "$root_dir" diff --cached --quiet || fail "deployment requires a clean index"
  test -z "$(git -C "$root_dir" ls-files --others --exclude-standard)" || fail "deployment rejects untracked files"

  local_sha=$(git -C "$root_dir" rev-parse HEAD)
  remote_sha=$(git -C "$root_dir" ls-remote --exit-code origin refs/heads/main | awk '{print $1}') || fail "origin/main is unavailable"
  test "$local_sha" = "$remote_sha" || fail "HEAD must be the exact SHA on origin/main"
  [[ "$local_sha" =~ ^[0-9a-f]{40}$ ]] || fail "release revision is not a full Git SHA"
  printf '%s\n' "$local_sha"
}

verify_terraform_inputs() {
  local name
  for name in \
    TF_VAR_domain_name TF_VAR_certificate_arn TF_VAR_cloudfront_certificate_arn \
    TF_VAR_vpc_id TF_VAR_public_subnet_ids \
    TF_VAR_private_subnet_ids TF_VAR_pioneer_secret_arn TF_VAR_sponsor_secret_arn \
    TF_VAR_alarm_topic_arn TF_VAR_origin_verify_header; do
    require_variable "$name"
  done
  if test "$manage_route53" = "true"; then
    require_variable TF_VAR_hosted_zone_id
  else
    require_variable HOSTIDO_DNS_PROJECT
    require_variable EVOX_DNS_ZONE
    require_variable EVOX_DNS_RECORD
  fi
}

verify_secret_version() {
  local secret_arn=$1 current_version
  current_version=$(aws secretsmanager list-secret-version-ids --secret-id "$secret_arn" --region "$aws_region" \
    --query "Versions[?contains(VersionStages, 'AWSCURRENT')].VersionId | [0]" --output text)
  test -n "$current_version" && test "$current_version" != "None" || fail "secret has no AWSCURRENT version: $secret_arn"
}

verify_secret_fields() {
  local secret_arn=$1 filter=$2
  if ! aws secretsmanager get-secret-value --secret-id "$secret_arn" --region "$aws_region" \
    --query SecretString --output text | jq -e "$filter" >/dev/null; then
    fail "secret is missing required non-empty configuration fields: $secret_arn"
  fi
}

repository_name() {
  printf '%s\n' "${1#*/}"
}

verify_ecr_repository() {
  local uri=$1 expected_registry account repository details mutability scan_on_push actual_uri
  expected_registry=${uri%%/*}
  account=$(aws sts get-caller-identity --query Account --output text)
  test "${expected_registry%%.*}" = "$account" || fail "ECR repository account does not match the active AWS identity"
  [[ "$expected_registry" == *".dkr.ecr.$aws_region.amazonaws.com" ]] || fail "ECR repository is outside AWS_REGION"
  repository=$(repository_name "$uri")
  details=$(aws ecr describe-repositories --region "$aws_region" --repository-names "$repository" \
    --query 'repositories[0].[imageTagMutability,imageScanningConfiguration.scanOnPush,repositoryUri]' --output text)
  read -r mutability scan_on_push actual_uri <<<"$details"
  test "$mutability" = "IMMUTABLE" || fail "ECR repository must enforce immutable tags: $repository"
  test "$scan_on_push" = "True" || fail "ECR repository must enable scan-on-push: $repository"
  test "$actual_uri" = "$uri" || fail "configured ECR URI does not match the repository"
}

verify_state_backend() {
  local versioning encryption public_access
  versioning=$(aws s3api get-bucket-versioning --bucket "$state_bucket" --query Status --output text)
  test "$versioning" = "Enabled" || fail "Terraform state bucket must have versioning enabled"
  encryption=$(aws s3api get-bucket-encryption --bucket "$state_bucket" \
    --query 'ServerSideEncryptionConfiguration.Rules[0].ApplyServerSideEncryptionByDefault.SSEAlgorithm' --output text)
  test "$encryption" = "aws:kms" || test "$encryption" = "AES256" || fail "Terraform state bucket must enforce server-side encryption"
  public_access=$(aws s3api get-public-access-block --bucket "$state_bucket" \
    --query 'PublicAccessBlockConfiguration.[BlockPublicAcls,IgnorePublicAcls,BlockPublicPolicy,RestrictPublicBuckets]' --output text)
  test "$public_access" = $'True\tTrue\tTrue\tTrue' || fail "Terraform state bucket must block all public access"
}

run_local_gates() {
  (
    cd "$root_dir"
    make test-unit
    make test-contract
    make test-integration
    make lint
    make build
  )
  trivy config --exit-code 1 --severity HIGH,CRITICAL \
    --skip-dirs "$root_dir/.venv" --skip-dirs "$root_dir/packages/web/node_modules" \
    --skip-dirs "$root_dir/packages/web/.next" "$root_dir"
  trivy filesystem --exit-code 1 --scanners vuln,secret --severity HIGH,CRITICAL \
    --skip-dirs "$root_dir/.venv" --skip-dirs "$root_dir/packages/web/node_modules" \
    --skip-dirs "$root_dir/packages/web/.next" "$root_dir"
}

login_to_ecr() {
  local registry=${api_repository%%/*}
  test "${web_repository%%/*}" = "$registry" || fail "API and web repositories must use the same ECR registry"
  aws ecr get-login-password --region "$aws_region" | docker login --username AWS --password-stdin "$registry" >/dev/null
}

image_exists() {
  local uri=$1 revision=$2 repository
  repository=$(repository_name "$uri")
  aws ecr describe-images --region "$aws_region" --repository-name "$repository" \
    --image-ids "imageTag=$revision" --query 'imageDetails[0].imageDigest' --output text >/dev/null 2>&1
}

image_digest() {
  local uri=$1 revision=$2 repository
  repository=$(repository_name "$uri")
  aws ecr describe-images --region "$aws_region" --repository-name "$repository" \
    --image-ids "imageTag=$revision" --query 'imageDetails[0].imageDigest' --output text
}

build_or_reuse_image() {
  local uri=$1 dockerfile=$2 revision=$3 label
  local image="$uri:$revision"
  if image_exists "$uri" "$revision"; then
    docker pull --platform "$container_platform" "$image" >/dev/null
  else
    docker buildx build --platform "$container_platform" --pull --no-cache --load \
      --build-arg "REVISION=$revision" --tag "$image" --file "$root_dir/$dockerfile" "$root_dir"
  fi

  label=$(docker image inspect --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image")
  test "$label" = "$revision" || fail "image source revision label does not match the release SHA: $image"
  if test "$dockerfile" = "Dockerfile.api"; then
    docker run --rm --platform "$container_platform" --entrypoint /bin/sh "$image" -ec \
      'command -v uvicorn >/dev/null && command -v evox-worker >/dev/null' \
      || fail "API image is missing the real API or worker entrypoint"
  else
    docker run --rm --platform "$container_platform" --entrypoint /bin/sh "$image" -ec \
      'test -x /app/node_modules/.bin/next' \
      || fail "web image is missing the real Next.js runtime entrypoint"
  fi
  trivy image --exit-code 1 --ignore-unfixed --severity HIGH,CRITICAL "$image"
  if ! image_exists "$uri" "$revision"; then
    docker push "$image"
  fi
}

capture_previous_task_definitions() {
  local cluster_response cluster_count cluster_failures response count failures active_count
  cluster_response=$(aws ecs describe-clusters --clusters "evox-$environment" --region "$aws_region" --output json) \
    || fail "unable to inspect the existing ECS cluster"
  cluster_count=$(printf '%s' "$cluster_response" | jq '.clusters | length')
  cluster_failures=$(printf '%s' "$cluster_response" | jq '.failures | length')
  if test "$cluster_count" -eq 0; then
    test "$cluster_failures" -eq 1 || fail "ECS cluster inspection returned an ambiguous result"
    test "$(printf '%s' "$cluster_response" | jq -r '.failures[0].reason')" = "MISSING" \
      || fail "ECS cluster inspection did not confirm an absent cluster"
    printf '[]\n'
    return
  fi
  test "$cluster_count" -eq 1 && test "$cluster_failures" -eq 0 \
    || fail "ECS cluster inspection returned an inconsistent result"
  test "$(printf '%s' "$cluster_response" | jq -r '.clusters[0].status')" = "ACTIVE" \
    || fail "existing ECS cluster is not active"

  response=$(aws ecs describe-services --cluster "evox-$environment" --services api web worker --region "$aws_region" --output json) \
    || fail "unable to inspect existing ECS services"
  count=$(printf '%s' "$response" | jq '.services | length')
  failures=$(printf '%s' "$response" | jq '.failures | length')
  if test "$count" -eq 0; then
    test "$failures" -eq 3 \
      && test "$(printf '%s' "$response" | jq '[.failures[].reason == "MISSING"] | all')" = "true" \
      || fail "ECS service inspection did not confirm a clean first deployment"
    printf '[]\n'
    return
  fi
  if test "$count" -ne 3 || test "$failures" -ne 0; then
    test "$((count + failures))" -eq 3 \
      && test "$(printf '%s' "$response" | jq '[.failures[].reason == "MISSING"] | all')" = "true" \
      || fail "safe rollback rejects an inconsistent partial ECS service set"
    active_count=$(printf '%s' "$response" | jq '[.services[] | select(.desiredCount > 0)] | length')
    test "$active_count" -eq 0 \
      || fail "safe first-deployment resume rejects active partial ECS services"
    printf '[]\n'
    return
  fi
  response=$(printf '%s' "$response" | jq '[.services[] | {service: .serviceName, taskDefinition, desiredCount}]')
  if test "$count" -eq 3; then
    active_count=$(printf '%s' "$response" | jq '[.[] | select(.desiredCount > 0)] | length')
    test "$active_count" -eq 0 || test "$active_count" -eq 3 || fail "safe rollback rejects mixed ECS desired counts"
    if test "$active_count" -eq 0; then
      response='[]'
    fi
  fi
  printf '%s\n' "$response"
}

terraform_init() {
  terraform -chdir="$terraform_dir" init -input=false -reconfigure \
    -backend-config="bucket=$state_bucket" \
    -backend-config="key=$state_key" \
    -backend-config="region=$aws_region"
}

apply_infrastructure() {
  local revision=$1 api_digest=$2 web_digest=$3 plan_dir plan_file
  plan_dir=$(mktemp -d "${TMPDIR:-/tmp}/evox-plan.XXXXXX")
  plan_file="$plan_dir/release.tfplan"
  if ! terraform -chdir="$terraform_dir" plan -input=false -lock-timeout=5m -out="$plan_file" \
    -var "aws_region=$aws_region" \
    -var "environment=$environment" \
    -var "image_tag=$revision" \
    -var "api_image_digest=$api_digest" \
    -var "web_image_digest=$web_digest" \
    -var "api_image_repository=$api_repository" \
    -var "web_image_repository=$web_repository"; then
    /bin/rm -rf "$plan_dir"
    return 1
  fi
  rollback_needed=true
  if ! terraform -chdir="$terraform_dir" apply -input=false -lock-timeout=5m "$plan_file"; then
    /bin/rm -rf "$plan_dir"
    return 1
  fi
  /bin/rm -rf "$plan_dir"
}

configure_external_dns() {
  local alb_domain cloudfront_domain
  test "$manage_route53" = "false" || return 0
  require_command uv
  test -d "$HOSTIDO_DNS_PROJECT" || fail "HOSTIDO_DNS_PROJECT is not a directory"
  alb_domain=$(terraform -chdir="$terraform_dir" output -raw alb_dns_name)
  cloudfront_domain=$(terraform -chdir="$terraform_dir" output -raw cloudfront_domain_name)
  (
    cd "$HOSTIDO_DNS_PROJECT"
    uv run hostido-dns upsert --domain "$EVOX_DNS_ZONE" --type CNAME \
      --name "origin-$EVOX_DNS_RECORD" --value "$alb_domain."
    uv run hostido-dns upsert --domain "$EVOX_DNS_ZONE" --type CNAME \
      --name "$EVOX_DNS_RECORD" --value "$cloudfront_domain."
  )
}

wait_for_readiness() {
  aws ecs wait services-stable --cluster "evox-$environment" --services api web worker --region "$aws_region"
}

rollback() {
  local previous=$1 item service task_definition
  printf 'deploy: ROLLBACK initiated\n' >&2
  if test "$(printf '%s' "$previous" | jq 'length')" -eq 0; then
    for service in api web worker; do
      aws ecs update-service --cluster "evox-$environment" --service "$service" --desired-count 0 --region "$aws_region" >/dev/null || true
    done
    aws ecs wait services-stable --cluster "evox-$environment" --services api web worker --region "$aws_region" || true
    return
  fi
  while IFS= read -r item; do
    service=$(printf '%s' "$item" | jq -r '.service')
    task_definition=$(printf '%s' "$item" | jq -r '.taskDefinition')
    aws ecs update-service --cluster "evox-$environment" --service "$service" \
      --task-definition "$task_definition" --force-new-deployment --region "$aws_region" >/dev/null
  done < <(printf '%s' "$previous" | jq -c '.[]')
  aws ecs wait services-stable --cluster "evox-$environment" --services api web worker --region "$aws_region" || true
}

verify_release() {
  local endpoint ready=false verification_status
  endpoint=$(terraform -chdir="$terraform_dir" output -raw public_url)
  for _attempt in {1..60}; do
    if curl --fail --silent --max-time 20 "$endpoint/" >/dev/null \
      && curl --fail --silent --max-time 20 "$endpoint/healthz" >/dev/null; then
      ready=true
      break
    fi
    sleep 10
  done
  test "$ready" = "true" || fail "public endpoint did not become ready: $endpoint"
  if (
    cd "$root_dir" \
      && EVOX_BASE_URL="$endpoint" EVOX_ALLOW_UNAVAILABLE_SPONSORS="$allow_unavailable_sponsors" make verify-live \
      && EVOX_BASE_URL="$endpoint" make smoke \
      && EVOX_E2E_BASE_URL="$endpoint" pnpm --filter @evox/web test:e2e:partial \
      && if test -n "${REPLAY_API_KEY:-}" && test "${EVOX_REPLAY_UPLOAD:-false}" = "true"; then
        EVOX_E2E_BASE_URL="$endpoint" pnpm --filter @evox/web test:replay:partial
      else
        true
      fi
  ) >&2; then
    :
  else
    verification_status=$?
    return "$verification_status"
  fi
  printf '%s\n' "$endpoint"
}

write_deployment_record() {
  local revision=$1 endpoint=$2 api_digest=$3 web_digest=$4 record_dir="$root_dir/evidence/deployments" task_definitions
  task_definitions=$(aws ecs describe-services --cluster "evox-$environment" --services api web worker --region "$aws_region" \
    --query 'services[].{service:serviceName,taskDefinition:taskDefinition}' --output json)
  mkdir -p "$record_dir"
  umask 077
  jq -n \
    --arg revision "$revision" \
    --arg environment "$environment" \
    --arg endpoint "$endpoint" \
    --arg cluster "evox-$environment" \
    --arg api_image "$api_repository@$api_digest" \
    --arg web_image "$web_repository@$web_digest" \
    --argjson task_definitions "$task_definitions" \
    '{revision: $revision, environment: $environment, endpoint: $endpoint, cluster: $cluster, images: {api: $api_image, web: $web_image}, task_definitions: $task_definitions, rollback: "restore the task definitions recorded by the preceding deployment", deployed_at: (now | todateiso8601)}' \
    >"$record_dir/deployment-record-$revision.json"
}

main() {
  local revision verified_revision previous endpoint api_digest web_digest rollback_needed=false
  for command in aws curl docker git jq make terraform trivy; do require_command "$command"; done
  test "$environment" = "production" || test "$environment" = "staging" || fail "EVOX_DEPLOY_ENVIRONMENT must be staging or production"
  test "$allow_unavailable_sponsors" = "true" || test "$allow_unavailable_sponsors" = "false" \
    || fail "EVOX_ALLOW_UNAVAILABLE_SPONSORS must be true or false"
  test "$manage_route53" = "true" || test "$manage_route53" = "false" \
    || fail "TF_VAR_manage_route53 must be true or false"
  case "$container_platform:$TF_VAR_cpu_architecture" in
    linux/amd64:X86_64|linux/arm64:ARM64) ;;
    *) fail "container platform and Fargate CPU architecture do not match" ;;
  esac
  [[ "$state_key" != /* && "$state_key" != *".."* ]] || fail "Terraform state key must be a safe relative object key"
  verify_terraform_inputs
  revision=$(verify_release_authority)
  aws sts get-caller-identity >/dev/null
  verify_state_backend
  verify_ecr_repository "$api_repository"
  verify_ecr_repository "$web_repository"
  verify_secret_version "$pioneer_secret_arn"
  verify_secret_version "$sponsor_secret_arn"
  verify_secret_fields "$pioneer_secret_arn" \
    '(.PIONEER_API_KEY // "") | type == "string" and length > 0'
  if test "$allow_unavailable_sponsors" = "true"; then
    verify_secret_fields "$sponsor_secret_arn" \
      '(.SENSO_API_KEY // "") | type == "string" and length > 0'
  else
    verify_secret_fields "$sponsor_secret_arn" \
      '[.SENSO_API_KEY, .ACTIAN_VECTORAI_URL, .ACTIAN_VECTORAI_ACCESS_TOKEN, .EVOX_ACTIAN_OUTCOME_COLLECTION, .EVOX_ACTIAN_VECTOR_SIZE, .EVOX_BAND_AGENT_ID, .EVOX_BAND_API_KEY, .EVOX_BAND_HUMAN_ID, .EVOX_BAND_HUMAN_HANDLE, .GUILD_WORKSPACE_ID, .GUILD_AGENT_ID, .REPLAY_API_KEY] | all(.[]; type == "string" and length > 0)'
  fi
  run_local_gates
  previous=$(capture_previous_task_definitions)
  login_to_ecr
  verified_revision=$(verify_release_authority)
  test "$verified_revision" = "$revision" \
    || fail "release revision changed after local verification gates"
  build_or_reuse_image "$api_repository" Dockerfile.api "$revision"
  build_or_reuse_image "$web_repository" Dockerfile.web "$revision"
  api_digest=$(image_digest "$api_repository" "$revision")
  web_digest=$(image_digest "$web_repository" "$revision")
  [[ "$api_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "API image digest is invalid"
  [[ "$web_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "web image digest is invalid"
  terraform_init
  trap 'if [ "$rollback_needed" = true ]; then rollback "$previous"; fi' ERR
  apply_infrastructure "$revision" "$api_digest" "$web_digest"
  configure_external_dns
  wait_for_readiness
  endpoint=$(verify_release)
  write_deployment_record "$revision" "$endpoint" "$api_digest" "$web_digest"
  rollback_needed=false
  trap - ERR
  printf 'deploy: release %s verified at %s\n' "$revision" "$endpoint"
}

main "$@"
