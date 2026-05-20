# 部署文档

## 本地 Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

Compose 会先启动一次性 `db-setup` 服务，自动执行 `alembic upgrade head` 并初始化供应商种子数据；`api` 和 `worker` 会等它成功完成后再启动。

生产镜像里已经包含 React 运维 UI，访问：

```text
http://localhost:8000/ops
```

`/ops` 入口有独立的运维密码保护，默认读取环境变量 `OPS_PASSWORD`。本地开发可以沿用 `.env.example` 中的默认值，真实环境应改成仅运维人员可知的强密码。

## 本地镜像验收环境

如果本机已有 PostgreSQL 或 Redis 占用端口，可以使用不暴露数据库端口的验收 Compose：

```bash
docker build -t notification-platform:local .
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e up -d
```

该环境会额外启动 `mock-vendor`，并自动迁移数据库和初始化供应商数据，用于验证 worker 对下游 HTTP API 的真实投递链路。API 映射到 `http://127.0.0.1:18000`。

## 服务

| 服务 | 说明 |
|---|---|
| `api` | FastAPI 后端，提供 API 和 `/ops` 运维 UI |
| `worker` | Dramatiq worker，与 `api` 使用同一个应用镜像 |
| `db-setup` | 一次性执行数据库迁移和供应商 seed，成功后退出 |
| `postgres` | PostgreSQL |
| `redis` | Redis broker |

## Worker 队列

Worker 启动入口是 `python -m scripts.run_worker`，启动时会执行：

1. 同步连接 PostgreSQL，从 `providers` 表读取所有 `enabled=true` 的供应商；
2. 取 `queue_name` 字段去重，逐个调用 `register_provider_actor(queue_name)` 注册 Dramatiq actor；
3. 通过环境变量让每个 Dramatiq worker 子进程导入模块时也注册这些 actor；
4. 使用 `--threads 1` 启动 Dramatiq，避免异步 SQLAlchemy 连接跨线程/跨 event loop 复用；
5. 如果没读到任何 enabled 供应商，**直接退出**，避免静默启动一个不监听任何队列的空 worker。

示例供应商使用的合法 Dramatiq 队列名：

```text
notifications_crm
notifications_ads
notifications_inventory
```

**新增供应商**之后必须**重启 worker**，新队列才会被监听。第一版不做运行时动态加队列。

## Stuck `delivering` 任务

`ACTOR_TIME_LIMIT_SECONDS`（默认 30 秒）作为 httpx 超时之外的兜底。如果 actor 在该时间内未完成（罕见情况，例如 DB IO 卡住），Dramatiq 会强制中止 actor，可能留下状态卡在 `delivering` 的任务。运维处理方式：

```sql
UPDATE notifications
SET status = 'retrying', updated_at = now()
WHERE status = 'delivering' AND updated_at < now() - interval '5 minutes';
```

之后再通过运维 UI 的"人工重试"或直接等下次重试触发即可。第一版**不**做自动 stale recovery。

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
