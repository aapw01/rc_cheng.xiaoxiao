# 部署文档

## 本地 Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

首次启动后执行数据库迁移和供应商种子数据：

```bash
uv run alembic upgrade head
uv run python -m scripts.seed_providers
```

生产镜像里已经包含 React 运维 UI，访问：

```text
http://localhost:8000/ops
```

## 本地镜像验收环境

如果本机已有 PostgreSQL 或 Redis 占用端口，可以使用不暴露数据库端口的验收 Compose：

```bash
docker build -t notification-platform:local .
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e up -d
```

该环境会额外启动 `mock-vendor`，用于验证 worker 对下游 HTTP API 的真实投递链路。API 映射到 `http://127.0.0.1:18000`。

## 服务

| 服务 | 说明 |
|---|---|
| `api` | FastAPI 后端，提供 API 和 `/ops` 运维 UI |
| `worker` | Dramatiq worker，与 `api` 使用同一个应用镜像 |
| `postgres` | PostgreSQL |
| `redis` | Redis broker |

## Worker 队列

Dramatiq 队列名使用合法标识：

```text
notifications_crm
notifications_ads
notifications_inventory
```

## GitHub Actions 镜像打包

`.github/workflows/docker-image.yml` 会使用同一个 `Dockerfile` 构建镜像，镜像包含：

- FastAPI API 服务；
- Dramatiq worker 运行代码；
- React 运维 UI 的生产静态文件。

触发规则：

| 事件 | 行为 |
|---|---|
| Pull Request | 只构建镜像，不推送 |
| push 到 `master`/`main` | 构建并推送 `ghcr.io/<owner>/<repo>:<branch>`、`sha-<commit>`，默认分支额外推送 `latest` |
| push tag `v*` | 构建并推送版本 tag 镜像 |

使用 GitHub Container Registry 需要仓库允许 workflow 写入 packages。部署时 API 和 worker 拉取同一个镜像，分别覆盖启动命令。
