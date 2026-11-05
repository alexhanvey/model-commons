set shell := ["bash", "-euo", "pipefail", "-c"]

default:
    @just --list

bootstrap:
    uv sync --all-packages
    pnpm --dir apps/web install
    test -f .env || cp .env.example .env
    @echo "Bootstrap complete. Fill in .env, then run 'just compose-up'."

dev:
    #!/usr/bin/env bash
    set -euo pipefail
    trap 'kill 0' EXIT INT TERM
    uv run uvicorn community_llm_api.main:app --reload --port "${API_PORT:-8000}" &
    PORT="${WEB_PORT:-3000}" pnpm --dir apps/web dev &
    wait

api:
    uv run uvicorn community_llm_api.main:app --reload --port "${API_PORT:-8000}"

inference:
    uv run uvicorn community_llm_inference.main:app --reload --port "${INFERENCE_PORT:-8001}"

web:
    PORT="${WEB_PORT:-3000}" pnpm --dir apps/web dev

worker:
    uv run community-llm-worker --help

test:
    uv run pytest

lint:
    uv run ruff check .
    uv run ruff format --check .
    pnpm --dir apps/web lint
    pnpm --dir apps/web format:check

format:
    uv run ruff format .
    pnpm --dir apps/web format

typecheck:
    uv run mypy apps packages ml
    pnpm --dir apps/web typecheck

check: lint typecheck test

build:
    pnpm --dir apps/web build
    docker build -f apps/api/Dockerfile -t community-llm-api .
    docker build -f apps/worker/Dockerfile -t community-llm-worker .
    docker build -f apps/inference/Dockerfile -t community-llm-inference .
    docker build -f apps/web/Dockerfile -t community-llm-web apps/web

compose-up:
    docker compose -f infra/compose/docker-compose.yml up -d --wait
    docker compose -f infra/compose/docker-compose.yml run --rm rustfs-init

compose-down:
    docker compose -f infra/compose/docker-compose.yml down

compose-logs:
    docker compose -f infra/compose/docker-compose.yml logs -f

migrate:
    uv run alembic -c apps/api/alembic.ini upgrade head

migration name:
    uv run alembic -c apps/api/alembic.ini revision --autogenerate -m "{{name}}"

seed:
    @echo "Database seed is added in Phase 2."

clean:
    rm -rf .pytest_cache .ruff_cache .mypy_cache
    find . -type d -name __pycache__ -prune -exec rm -rf {} +
