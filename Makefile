# arvel-ecommerce-kit — common tasks. `make help` lists them.
.DEFAULT_GOAL := help
.PHONY: help install env up down setup migrate fresh seed serve worker schedule test typecheck lint check

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies (arvel from ../arvel)
	uv sync --extra dev

env: ## Create .env from the template if missing
	@test -f .env || (cp .env.example .env && echo "created .env")

up: ## Start all infrastructure (Postgres, Valkey, RabbitMQ, Meilisearch, RustFS, Keycloak, Mailpit)
	docker compose up -d

down: ## Stop all infrastructure
	docker compose down --remove-orphans --volumes

setup: install env up ## One-shot: deps + .env + infra + key + migrate + seed
	@echo "waiting for Postgres..." && until docker compose exec -T db pg_isready -U arvel -d arvel_ecommerce_kit >/dev/null 2>&1; do sleep 1; done
	uv run arvel key:generate
	uv run arvel migrate:fresh
	uv run arvel db:seed
	@echo "\nReady. 'make serve' → http://127.0.0.1:8000 (API docs at /docs)"

migrate: ## Apply outstanding migrations
	uv run arvel migrate

fresh: ## Drop all tables, re-migrate, and re-seed
	uv run arvel migrate:fresh && uv run arvel db:seed

seed: ## Seed demo data (downloads product images via the Http client)
	uv run arvel db:seed

serve: ## Run the dev server (http://127.0.0.1:8000)
	uv run arvel serve

worker: ## Run a queue worker
	uv run arvel queue:work

schedule: ## Run due scheduled tasks
	uv run arvel schedule:run

test: ## Run the test suite (in-process sqlite; no infra needed)
	uv run pytest

typecheck: ## Strict type-check the app code
	uv run pyright

lint: ## Lint + format check
	uv run ruff check . && uv run ruff format --check .

check: lint typecheck test ## Lint + types + tests
