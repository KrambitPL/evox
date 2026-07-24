.PHONY: install test-unit test-contract test-integration e2e test-replay lint build infra-check verify-live smoke deploy

install:
	uv sync --all-packages --all-groups
	pnpm install --frozen-lockfile

test-unit:
	uv run --package evox-api pytest packages/api/tests

test-contract:
	uv run --package evox-api pytest packages/api/tests/contract

test-integration:
	uv run --package evox-api pytest packages/api/tests/integration

e2e:
	pnpm --filter @evox/web test:e2e

test-replay:
	@test -n "$$REPLAY_API_KEY" || (echo "REPLAY_API_KEY is required for Replay upload." >&2; exit 2)
	@test "$${EVOX_REPLAY_UPLOAD:-}" = "true" || (echo "Set EVOX_REPLAY_UPLOAD=true to authorize Replay recording upload." >&2; exit 2)
	pnpm --filter @evox/web test:replay

lint:
	uv run --package evox-api ruff check packages/api/src packages/api/tests

build:
	pnpm --filter @evox/web build

infra-check:
	terraform -chdir=infra/terraform fmt -check -recursive
	terraform -chdir=infra/terraform init -backend=false -input=false
	terraform -chdir=infra/terraform validate
	shellcheck scripts/deploy.sh scripts/tests/test_deploy_contract.sh
	./scripts/tests/test_deploy_contract.sh

verify-live:
	./scripts/verify_live.sh

smoke:
	./scripts/smoke.sh

deploy:
	./scripts/deploy.sh
