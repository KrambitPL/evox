.PHONY: install test-unit test-contract test-integration e2e test-replay lint build infra-check verify-live smoke deploy

install:
	uv sync --all-packages --all-groups
	pnpm install --frozen-lockfile

test-unit:
	uv run --package evox-api pytest packages/api/tests

test-contract:
	uv run --package evox-api pytest packages/api/tests/contract

test-integration:
	@echo "Integration tests are not implemented yet; run the agent-2 persistence lane first." >&2
	@exit 2

e2e:
	@echo "End-to-end tests are not implemented yet; run the agent-11 web lane first." >&2
	@exit 2

test-replay:
	@echo "Replay verification is not implemented yet; run the agent-13 browser QA lane first." >&2
	@exit 2

lint:
	uv run --package evox-api ruff check packages/api/src packages/api/tests

build:
	@echo "Web build is not implemented yet; run the agent-11 web lane first." >&2
	@exit 2

infra-check:
	terraform -chdir=infra/terraform fmt -check -recursive
	terraform -chdir=infra/terraform init -backend=false -input=false
	terraform -chdir=infra/terraform validate
	shellcheck scripts/deploy.sh scripts/tests/test_deploy_contract.sh
	./scripts/tests/test_deploy_contract.sh

verify-live:
	@echo "Live sponsor verification is not implemented yet; run the agent-15 live QA lane first." >&2
	@exit 2

smoke:
	@echo "Deployment smoke verification is not implemented yet; run the agent-15 live QA lane first." >&2
	@exit 2

deploy:
	./scripts/deploy.sh
