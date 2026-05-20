# API 通知投递平台

企业内部 API 通知投递平台：业务系统提交业务事件，平台异步转换并投递到外部供应商 HTTP API，记录投递尝试、失败重试，并提供运维页面查看和操作。

作业要求中的 AI 使用说明见 [AI_USAGE.md](AI_USAGE.md)，其中记录了 AI 提供的帮助、未采纳建议，以及关键工程决策与取舍。

## 快速开始

```bash
cp .env.example .env
PROVIDER_CRM_BASE_URL=http://mock-vendor:9000 docker compose --profile mock up --build
```

使用 GitHub Actions 已打包镜像启动时，也需要把 CRM 地址指向 mock vendor：

```bash
cp .env.example .env
IMAGE=ghcr.io/aapw01/rc_cheng.xiaoxiao:master \
PROVIDER_CRM_BASE_URL=http://mock-vendor:9000 \
docker compose --profile mock up --no-build
```

Docker 启动会自动执行 Alembic 迁移并初始化供应商种子数据。默认入口：

| 服务 | 地址 |
|---|---|
| API | `http://localhost:18000` |
| 运维 UI | `http://localhost:18000/ops` |
| API 文档 | `http://localhost:18000/docs` |

运维 UI 默认密码见 `.env` 的 `OPS_PASSWORD`。

常用本地配置：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `API_KEY` | `dev-api-key` | 调用 API 时放到 `X-API-Key` |
| `OPS_PASSWORD` | `dev-ops-password` | 登录 `/ops` 的运维密码 |
| `API_PORT` | `18000` | API 和运维 UI 暴露端口 |
| `POSTGRES_PORT` | `5432` | 本机 PostgreSQL 端口，冲突时可改 |
| `REDIS_PORT` | `6379` | 本机 Redis 端口，冲突时可改 |

## Curl 验证

健康检查：

```bash
curl -fsS http://127.0.0.1:18000/health
```

提交通知：

```bash
curl -sS -X POST http://127.0.0.1:18000/api/notifications \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-api-key' \
  -d '{
    "provider_code": "crm",
    "event_type": "subscription_paid",
    "event_id": "local_test_001",
    "payload": {
      "user_id": "u_123",
      "email": "a@example.com",
      "subscription_id": "sub_001",
      "amount": 19900,
      "currency": "USD",
      "paid_at": "2026-05-19T10:00:00Z"
    },
    "metadata": {
      "trace_id": "local_trace_001"
    }
  }' | jq .
```

查看投递结果：

```bash
curl -sS 'http://127.0.0.1:18000/api/admin/notifications/<notification_id>' \
  -H 'X-API-Key: dev-api-key' | jq .
```

查询任务列表：

```bash
curl -sS 'http://127.0.0.1:18000/api/admin/notifications?provider_code=crm&limit=5' \
  -H 'X-API-Key: dev-api-key' | jq .
```

没有安装 `jq` 时，去掉命令末尾的 `| jq .` 即可。

如果要换端口启动：

```bash
API_PORT=8000 POSTGRES_PORT=15432 REDIS_PORT=16379 \
  PROVIDER_CRM_BASE_URL=http://mock-vendor:9000 \
  docker compose --profile mock up --build
```

## 本地开发

```bash
uv sync
npm --prefix web install
docker compose up -d postgres redis
uv run alembic upgrade head
uv run python -m scripts.seed_providers
uv run uvicorn app.main:app --reload
npm --prefix web run dev
```

## 技术栈

| 模块 | 技术 |
|---|---|
| API | FastAPI, Pydantic |
| 数据库 | PostgreSQL, SQLAlchemy, Alembic |
| 队列 | Redis, Dramatiq |
| HTTP 投递 | httpx |
| 前端 | React, Vite, Ant Design |
| 测试 | pytest, pytest-httpx |

## 项目结构

| 路径 | 说明 |
|---|---|
| `app/` | 后端 API、模型、服务、worker |
| `web/` | React 运维页面 |
| `alembic/` | 数据库迁移 |
| `scripts/` | 种子数据脚本 |
| `tests/` | 单元测试和集成测试 |
| `docs/` | API、数据库、部署、测试和设计文档 |

## 常用命令

| 命令 | 用途 |
|---|---|
| `make test` | 运行后端测试 |
| `make lint` | 运行 ruff 检查 |
| `make migrate` | 执行数据库迁移 |
| `make seed` | 初始化供应商 |
| `make web-build` | 构建前端 |
| `make docker-up` | 启动完整环境 |

## Docker Compose

项目只保留一个 Compose 文件：[docker-compose.yml](docker-compose.yml)，同时支持本地测试和使用 GitHub Actions 打包出的镜像。

| 场景 | 命令 |
|---|---|
| 本地构建并启动 | `docker compose up --build` |
| 使用上游镜像启动 | `IMAGE=ghcr.io/aapw01/rc_cheng.xiaoxiao:master docker compose up -d --no-build` |
| 启动 mock vendor 做端到端测试 | `PROVIDER_CRM_BASE_URL=http://mock-vendor:9000 docker compose --profile mock up --build` |
| 使用上游镜像并启动 mock vendor | `IMAGE=ghcr.io/aapw01/rc_cheng.xiaoxiao:master PROVIDER_CRM_BASE_URL=http://mock-vendor:9000 docker compose --profile mock up --no-build` |

## 镜像打包

GitHub Actions 会在 push、PR 和 tag 时构建统一 Docker 镜像；非 PR 事件会推送到 GitHub Container Registry。API 和 worker 使用同一个镜像，通过不同 command 启动。

## 环境变量

见 [.env.example](.env.example)。

## 新增供应商

参考 [供应商接入文档](docs/provider-onboarding.md)。简要流程：

1. 实现 `app/providers/adapters/<provider_code>.py` 并继承 `ProviderAdapter`；
2. 在 `app/providers/registry.py` 注册；
3. 把供应商凭证加到 `app/config.py` 和 `.env.example`；
4. 在 `scripts/seed_providers.py` 增加 seed 记录（`enabled=true`、独立的 `queue_name`）；
5. 在 PostgreSQL 上执行 seed（`uv run python -m scripts.seed_providers`）；
6. **重启 worker** —— `scripts/run_worker.py` 会从 DB 重新读取 enabled queue 并注册新 actor。

第一版**不**支持运行时动态新增队列，新增供应商必须重启 worker。

## 后续演进

第一版优先保证可靠投递主链路和可交付性，以下能力暂未实现，可作为后续迭代方向：

- 自动熔断：按供应商统计连续失败或窗口失败率，自动暂停异常供应商；
- 恢复探测：供应商故障恢复后，通过安全探测或人工确认恢复投递；
- 供应商配置热加载：新增或修改供应商后，无需重启 worker 即可加载新队列和配置；
- 供应商管理 UI：支持查看供应商配置、版本、启停记录和变更历史；
- 配置化供应商协议：用 DSL 或模板描述 URL、Header、Query、Body、认证和签名规则；
- 更多认证方式：Basic Auth、OAuth token 刷新等；
- 更细的队列策略：从“一供应商一队列”演进为队列池，避免供应商过多导致队列无限扩张；
- Stuck 任务恢复：自动扫描长时间停留在 `delivering` 的任务并进入人工处理或重试流程；
- 链路追踪：让 `trace_id` 贯穿 API、worker、供应商请求、日志和运维 UI；
- 可观测性平台：接入 OpenTelemetry、Prometheus、Grafana，延迟、吞吐、失败率和队列堆积指标；
- 自动告警：对失败率、堆积量、重试次数、供应商暂停等事件接入告警系统；
- 自动扩缩容：服务根据任务数量自动扩缩容。

## 文档

- [API 文档](docs/api.md)
- [数据库文档](docs/database.md)
- [部署文档](docs/deployment.md)
- [测试文档](docs/testing.md)
- [供应商接入文档](docs/provider-onboarding.md)
