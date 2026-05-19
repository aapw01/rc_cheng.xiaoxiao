# API 通知投递平台

企业内部 API 通知投递平台：业务系统提交业务事件，平台异步转换并投递到外部供应商 HTTP API，记录投递尝试、失败重试，并提供运维页面查看和操作。

## 快速开始

```bash
cp .env.example .env
uv sync
npm --prefix web install
docker compose up -d postgres redis
uv run alembic upgrade head
uv run python scripts/seed_providers.py
uv run uvicorn app.main:app --reload
```

前端开发：

```bash
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

## 环境变量

见 [.env.example](.env.example)。

## 文档

- [API 文档](docs/api.md)
- [数据库文档](docs/database.md)
- [部署文档](docs/deployment.md)
- [测试文档](docs/testing.md)
- [供应商接入文档](docs/provider-onboarding.md)

