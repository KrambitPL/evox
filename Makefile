.PHONY: install test-unit test-contract test-integration e2e test-replay lint build verify-live smoke deploy

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
	pnpm --filter @evox/web test:e2e

test-replay:
	@test -n "$$REPLAY_API_KEY" || (echo "REPLAY_API_KEY is required for Replay upload." >&2; exit 2)
	@test "$${EVOX_REPLAY_UPLOAD:-}" = "true" || (echo "Set EVOX_REPLAY_UPLOAD=true to authorize Replay recording upload." >&2; exit 2)
	pnpm --filter @evox/web test:replay

lint:
	uv run --package evox-api ruff check packages/api/src packages/api/tests

build:
	@echo "Web build is not implemented yet; run the agent-11 web lane first." >&2
	@exit 2

verify-live:
	@echo "Live sponsor verification is not implemented yet; run the agent-15 live QA lane first." >&2
	@exit 2

smoke:
	@echo "Deployment smoke verification is not implemented yet; run the agent-15 live QA lane first." >&2
	@exit 2

deploy:
	@echo "Deployment is not implemented yet; run the agent-12 infrastructure lane first." >&2
	@exit 2
