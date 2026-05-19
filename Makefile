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
	uv run python scripts/seed_providers.py

docker-up:
	docker compose up --build

docker-down:
	docker compose down

web-build:
	npm --prefix web run build

