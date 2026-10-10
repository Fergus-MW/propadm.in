.PHONY: install dev dev-docker seed test check lint typecheck build infra-check schema-check api-check stop
install:
	uv sync --locked
	pnpm install --frozen-lockfile

dev:
	uv run python infra/scripts/dev.py

dev-docker:
	docker compose -f compose.yaml -f compose.dev.yaml up --build --renew-anon-volumes

stop:
	docker compose down

seed:
	uv run python -m db.seed.load

test:
	uv run pytest
	pnpm --dir services/admin-panel test
	node --test landing/test/server.test.mjs

lint:
	uv run ruff check packages services db infra/scripts infra/tests tests

typecheck:
	pnpm --dir services/admin-panel typecheck

build:
	pnpm --dir services/admin-panel build

api-check:
	pnpm --dir services/admin-panel generate:api --check

infra-check:
	terraform fmt -check -recursive infra
	terraform -chdir=infra/bootstrap init -backend=false -input=false
	terraform -chdir=infra/bootstrap validate
	terraform -chdir=infra/main init -backend=false -input=false
	terraform -chdir=infra/main validate
	docker compose config --quiet
	docker compose -f compose.yaml -f compose.dev.yaml config --quiet

schema-check:
	uv run python db/schema/generate.py
	uv run python -m db.schema.apply --create-database

check: lint test typecheck build infra-check api-check
