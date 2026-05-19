# 部署文档

## 本地 Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

首次启动后执行：

```bash
uv run alembic upgrade head
uv run python scripts/seed_providers.py
```

## 服务

| 服务 | 说明 |
|---|---|
| `api` | FastAPI 后端 |
| `worker` | Dramatiq worker |
| `postgres` | PostgreSQL |
| `redis` | Redis broker |
| `web` | React 运维页面 |

## Worker 队列

Dramatiq 队列名使用合法标识：

```text
notifications_crm
notifications_ads
notifications_inventory
```

