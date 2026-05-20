.PHONY: sync test lint format dev migrate seed docker-up docker-down web-build

sync:
	uv sync
	npm --prefix web install

test:
	uv run pytest -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m scripts.seed_providers

docker-up:
	docker compose -f docker-compose.e2e.yml up --build

docker-down:
	docker compose -f docker-compose.e2e.yml down

web-build:
	npm --prefix web run build
