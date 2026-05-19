# API 文档

所有业务 API 和运维 API 使用 `X-API-Key` 鉴权。

## 提交通知

`POST /api/notifications`

```json
{
  "provider_code": "crm",
  "event_type": "subscription_paid",
  "event_id": "sub_paid_202605190001",
  "payload": {
    "user_id": "u_123",
    "email": "a@example.com",
    "subscription_id": "sub_001",
    "amount": 19900,
    "currency": "USD",
    "paid_at": "2026-05-19T10:00:00Z"
  },
  "metadata": {
    "source_system": "billing",
    "trace_id": "trace_abc123"
  }
}
```

成功返回 `202 Accepted`。重复提交同一 `provider_code + event_type + event_id` 返回已有 notification。

## 查询通知

`GET /api/notifications/{id}`

返回当前状态、payload、metadata 和尝试次数。

## 运维 API

| Endpoint | 说明 |
|---|---|
| `GET /api/admin/metrics` | Dashboard 指标 |
| `GET /api/admin/providers` | 供应商列表 |
| `POST /api/admin/providers/{provider_code}/pause` | 暂停供应商新任务 |
| `POST /api/admin/providers/{provider_code}/resume` | 恢复供应商新任务 |
| `GET /api/admin/notifications` | 通知列表，支持 provider/status 筛选 |
| `GET /api/admin/notifications/{id}` | 通知详情和 attempts |
| `POST /api/admin/notifications/{id}/retry` | failed 任务人工重试 |

