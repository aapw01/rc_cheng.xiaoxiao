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

## 集成测试覆盖

- API 创建 notification；
- worker 投递到 mock vendor；
- 2xx 成功进入 `delivered`；
- 失败记录 `delivery_attempts` 并进入 `retrying` 或 `failed`；
- 重复提交同一事件不会创建重复任务；
- 暂停供应商后新提交被拒绝；
- failed 任务可人工重试。

