# 测试文档

## 后端测试

```bash
uv run pytest -v
```

## 指定测试

```bash
uv run pytest tests/providers/test_adapters.py -v
uv run pytest tests/api/test_notifications.py -v
uv run pytest tests/integration/test_delivery_flow.py -v
```

## 前端构建验证

```bash
npm --prefix web run build
```

## 容器端到端验收

`docker-compose.e2e.yml` 使用本地统一镜像、PostgreSQL、Redis 和 mock vendor 验证真实异步链路：

```bash
docker build -t notification-platform:local .
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e up -d
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e exec -T api uv run alembic upgrade head
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e exec -T api uv run python -m scripts.seed_providers
curl -fsS http://127.0.0.1:18000/health
```

提交一条 CRM 通知后，预期任务最终变为 `delivered`，`delivery_attempts.response_status=200`，mock vendor 日志能看到收到的 HTTP 请求。验收结束后清理：

```bash
docker compose -f docker-compose.e2e.yml -p rc-notify-e2e down -v
```

## 集成测试覆盖

- API 创建 notification；
- worker 投递到 mock vendor；
- 2xx 成功进入 `delivered`；
- 失败记录 `delivery_attempts` 并进入 `retrying` 或 `failed`；
- 重复提交同一事件不会创建重复任务；
- 暂停供应商后新提交被拒绝；
- failed 任务可人工重试。
