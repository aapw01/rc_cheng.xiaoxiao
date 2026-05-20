# API 通知投递平台

企业内部 API 通知投递平台：业务系统提交业务事件，平台异步转换并投递到外部供应商 HTTP API，记录投递尝试、失败重试，并提供运维页面查看和操作。

## 快速开始

```bash
cp .env.example .env
uv sync
npm --prefix web install
docker compose up -d postgres redis
uv run alembic upgrade head
uv run python -m scripts.seed_providers
uv run uvicorn app.main:app --reload
```

前端开发：

```bash
npm --prefix web run dev
```

Docker 完整环境：

```bash
docker compose up --build
```

运维 UI 生产入口为 `http://localhost:8000/ops`。

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

## 文档

- [API 文档](docs/api.md)
- [数据库文档](docs/database.md)
- [部署文档](docs/deployment.md)
- [测试文档](docs/testing.md)
- [供应商接入文档](docs/provider-onboarding.md)
