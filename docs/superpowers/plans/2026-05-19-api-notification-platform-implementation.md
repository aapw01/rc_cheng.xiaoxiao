# API Notification Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deliverable API notification platform described in `docs/superpowers/specs/2026-05-19-api-notification-platform-design.md`.

**Architecture:** FastAPI accepts business events, stores durable notification state in PostgreSQL, enqueues Dramatiq delivery actors through Redis, and provider adapters translate events into vendor HTTP calls. A React/Vite operations UI reads admin APIs for dashboard, provider operations, notification browsing, and manual retry.

**Tech Stack:** Python 3.12+ with uv, FastAPI, SQLAlchemy async, Alembic, PostgreSQL, Redis, Dramatiq, httpx, pytest, React/Vite, Ant Design, Docker Compose.

---

## File Structure

Backend:

- `pyproject.toml`: uv project metadata, Python dependencies, pytest and ruff config.
- `.env.example`: documented environment variables.
- `app/config.py`: Pydantic settings.
- `app/db.py`: async SQLAlchemy engine/session.
- `app/models.py`: ORM models and enums.
- `app/schemas.py`: API request/response schemas.
- `app/errors.py`: API error types and handlers.
- `app/security.py`: API key dependency.
- `app/providers/base.py`: adapter protocol and request/result types.
- `app/providers/registry.py`: provider registry and queue actor mapping.
- `app/providers/adapters/*.py`: sample provider adapters.
- `app/services/notifications.py`: submit, duplicate handling, provider checks, manual retry.
- `app/services/delivery.py`: claim task, build request, execute HTTP call, record attempts, status transitions.
- `app/services/metrics.py`: admin dashboard aggregation.
- `app/tasks/broker.py`: Dramatiq broker setup.
- `app/tasks/delivery.py`: per-queue actors delegating to shared delivery function.
- `app/api/notifications.py`: business notification endpoints.
- `app/api/admin.py`: admin endpoints.
- `app/main.py`: FastAPI app wiring.
- `alembic/`: database migrations.
- `scripts/seed_providers.py`: idempotent provider seed.
- `tests/`: unit and integration-oriented tests.

Frontend:

- `web/package.json`: React/Vite project.
- `web/src/api.ts`: API client.
- `web/src/App.tsx`: layout and route state.
- `web/src/pages/*.tsx`: dashboard, providers, notifications, detail.
- `web/src/main.tsx`, `web/src/styles.css`: app entry and styling.

Docs/infra:

- `README.md`: concise project overview and quick start.
- `docs/api.md`: API examples and semantics.
- `docs/database.md`: table and index documentation.
- `docs/deployment.md`: Docker Compose setup.
- `docs/testing.md`: unit and integration test commands.
- `Dockerfile`, `docker-compose.yml`, `Makefile`: local and container workflows.

## Tasks

### Task 1: Backend Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/config.py`
- Create: `app/main.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write failing health test**

Create `tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_health.py -v`

Expected: fail because project dependencies or `app.main` do not exist.

- [ ] **Step 3: Add scaffold**

Create `pyproject.toml`, `.env.example`, `.gitignore`, `app/config.py`, and `app/main.py` with FastAPI app and `/health`.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_health.py -v`

Expected: pass.

### Task 2: Database Models and Alembic

**Files:**
- Create: `app/db.py`
- Create: `app/models.py`
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/0001_initial.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write model metadata test**

Create `tests/test_models.py` to assert the provider, notification, delivery attempt, and operator action tables exist and the notification unique constraint is present.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_models.py -v`

Expected: fail because models are missing.

- [ ] **Step 3: Implement ORM models**

Create enums and models for providers, notifications, delivery attempts, and operator actions. Include unique `(provider_code, event_type, event_id)`.

- [ ] **Step 4: Add Alembic migration**

Create initial migration matching the ORM models.

- [ ] **Step 5: Run model tests**

Run: `uv run pytest tests/test_models.py -v`

Expected: pass.

### Task 3: Provider Adapter Layer

**Files:**
- Create: `app/providers/__init__.py`
- Create: `app/providers/base.py`
- Create: `app/providers/registry.py`
- Create: `app/providers/adapters/crm.py`
- Create: `app/providers/adapters/ads.py`
- Create: `app/providers/adapters/inventory.py`
- Create: `tests/providers/test_adapters.py`

- [ ] **Step 1: Write adapter tests**

Cover CRM `subscription_paid`, ads `user_registered`, inventory `order_created`, unsupported event rejection, and success status policy.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/providers/test_adapters.py -v`

Expected: fail because adapters do not exist.

- [ ] **Step 3: Implement adapter base and sample adapters**

Implement `AdapterRequest`, `ProviderAdapter`, `ProviderAdapterError`, sample adapters, and registry helpers.

- [ ] **Step 4: Run adapter tests**

Run: `uv run pytest tests/providers/test_adapters.py -v`

Expected: pass.

### Task 4: Notification Submission API

**Files:**
- Create: `app/schemas.py`
- Create: `app/errors.py`
- Create: `app/security.py`
- Create: `app/services/notifications.py`
- Create: `app/api/notifications.py`
- Modify: `app/main.py`
- Create: `tests/api/test_notifications.py`

- [ ] **Step 1: Write API tests**

Cover valid submit returns `202`, duplicate submit returns same notification ID, unknown provider returns 400/404-style error, paused provider blocks only new submissions, and status lookup returns current state.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_notifications.py -v`

Expected: fail because API/service code is missing.

- [ ] **Step 3: Implement schemas, errors, security, and service**

Implement API key header, unified error response, notification creation with duplicate-first behavior, provider paused/disabled checks only for new tasks.

- [ ] **Step 4: Implement routes**

Register `POST /api/notifications` and `GET /api/notifications/{id}`.

- [ ] **Step 5: Run API tests**

Run: `uv run pytest tests/api/test_notifications.py -v`

Expected: pass.

### Task 5: Dramatiq Broker, Queue Actors, and Delivery Service

**Files:**
- Create: `app/tasks/__init__.py`
- Create: `app/tasks/broker.py`
- Create: `app/tasks/delivery.py`
- Create: `app/services/delivery.py`
- Create: `tests/services/test_delivery.py`
- Create: `tests/tasks/test_queue_routing.py`

- [ ] **Step 1: Write delivery service tests**

Cover task claim by conditional update, duplicate actor exits when claim fails, successful httpx response marks delivered, failed response records attempt and raises retryable exception, max attempts marks failed.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/services/test_delivery.py tests/tasks/test_queue_routing.py -v`

Expected: fail because delivery service and actors are missing.

- [ ] **Step 3: Implement delivery service**

Implement shared `deliver_notification(notification_id)` business function with claim, adapter request construction, httpx timeout, attempt logging, and status transitions.

- [ ] **Step 4: Implement Dramatiq broker and per-queue actors**

Implement fixed actors for CRM, ads, and inventory queues. Map provider queue to actor in registry/enqueue helper.

- [ ] **Step 5: Run delivery tests**

Run: `uv run pytest tests/services/test_delivery.py tests/tasks/test_queue_routing.py -v`

Expected: pass.

### Task 6: Admin APIs and Metrics

**Files:**
- Create: `app/services/metrics.py`
- Create: `app/api/admin.py`
- Modify: `app/main.py`
- Create: `tests/api/test_admin.py`

- [ ] **Step 1: Write admin tests**

Cover metrics aggregation, providers list, pause/resume provider, notification list filtering, notification detail with attempts, and failed manual retry.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/api/test_admin.py -v`

Expected: fail because admin APIs are missing.

- [ ] **Step 3: Implement admin services and routes**

Implement endpoints from the spec and operator action logging for pause/resume/retry.

- [ ] **Step 4: Run admin tests**

Run: `uv run pytest tests/api/test_admin.py -v`

Expected: pass.

### Task 7: Seed Data and Integration Tests

**Files:**
- Create: `scripts/seed_providers.py`
- Create: `tests/integration/test_delivery_flow.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Write integration tests**

Cover submit -> enqueue -> worker function -> mock vendor success, mock vendor failure to retry/failed, duplicate submit, pause blocking new submit, manual retry.

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/integration/test_delivery_flow.py -v`

Expected: fail because seed/test plumbing is incomplete.

- [ ] **Step 3: Implement seed script and test fixtures**

Add idempotent provider seed and async database fixtures.

- [ ] **Step 4: Run integration tests**

Run: `uv run pytest tests/integration/test_delivery_flow.py -v`

Expected: pass.

### Task 8: React Operations UI

**Files:**
- Create: `web/package.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`
- Create: `web/src/api.ts`
- Create: `web/src/pages/Dashboard.tsx`
- Create: `web/src/pages/Providers.tsx`
- Create: `web/src/pages/Notifications.tsx`
- Create: `web/src/pages/NotificationDetail.tsx`
- Create: `web/src/styles.css`

- [ ] **Step 1: Add frontend scaffold and API client**

Use Vite + React + TypeScript + Ant Design. API base URL reads `VITE_API_BASE_URL`.

- [ ] **Step 2: Implement pages**

Dashboard shows metrics, Providers supports pause/resume, Notifications supports filters, Detail shows attempts and retry action.

- [ ] **Step 3: Run frontend build**

Run: `npm --prefix web run build`

Expected: pass.

### Task 9: Docker, Makefile, and Documentation

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `Makefile`
- Create: `README.md`
- Create: `docs/api.md`
- Create: `docs/database.md`
- Create: `docs/deployment.md`
- Create: `docs/testing.md`
- Modify: `.env.example`

- [ ] **Step 1: Add container and command workflow**

Create Docker Compose services for api, worker, postgres, redis, and web.

- [ ] **Step 2: Add docs**

Document quick start, API examples, schema, deployment, and tests.

- [ ] **Step 3: Run verification**

Run:

```bash
uv run pytest -v
uv run ruff check .
npm --prefix web run build
docker compose config
```

Expected: all pass.

## Self-Review

Spec coverage:

- API shape, metadata, provider adapters, queues, retry, idempotency, pause/resume, admin UI, docs, and tests are covered by Tasks 1-9.
- First-version exclusions are captured in adapter design, retry config, no dynamic queue creation, no callback URL, no auto circuit breaker, no DSL, no `next_retry_at`.
- `AI_USAGE.md` is intentionally not part of this implementation plan because the spec states it is outside this implementation document.

No placeholders:

- The plan uses concrete file paths, commands, and expected outcomes. Code details will be produced inside each TDD task rather than pre-expanding every file into the plan document.
