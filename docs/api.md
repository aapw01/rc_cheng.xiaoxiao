# API 文档

所有业务 API 和运维 API 都使用 `X-API-Key` 鉴权。成功响应的 `code` 为 `0`，失败响应的 `code` 为字符串错误码。

## 通用约定

请求 Header：

```http
X-API-Key: dev-api-key
Content-Type: application/json
```

响应格式：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

错误响应：

```json
{
  "code": "validation_error",
  "message": "Request validation failed",
  "data": null
}
```

通知状态：`pending`、`delivering`、`retrying`、`delivered`、`failed`。

## 提交通知

`POST /api/notifications`

业务系统提交标准化事件，平台根据 `provider_code + event_type` 选择供应商适配器并异步投递。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `provider_code` | string | 是 | 供应商编码，当前支持 `crm`、`ads`、`inventory` |
| `event_type` | string | 是 | 事件类型，必须被对应供应商支持 |
| `event_id` | string | 是 | 业务事件唯一 ID，用于幂等去重 |
| `occurred_at` | string/null | 否 | 事件发生时间，ISO 8601 |
| `payload` | object | 是 | 业务事件数据，由供应商适配器校验 |
| `metadata` | object | 否 | 调用方元数据，例如 `trace_id` |

示例：

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

成功返回 `202 Accepted`：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": "3b7091af-d3aa-451a-81c0-b75185837cbc",
    "provider_code": "crm",
    "event_type": "subscription_paid",
    "event_id": "sub_paid_202605190001",
    "status": "pending",
    "attempt_count": 0,
    "last_error": null,
    "payload": {},
    "metadata": {},
    "created_at": "2026-05-19T10:00:00Z",
    "updated_at": "2026-05-19T10:00:00Z"
  }
}
```

幂等规则：

- 平台以 `provider_code + event_type + event_id` 作为唯一业务事件；
- 重复提交同一事件会返回已有 notification，仍返回 `202`，不会创建新任务；
- 重复提交优先于 provider 状态检查，因此 provider 已暂停时，重复提交已有事件仍会返回已有 notification；
- **如果旧任务已经处于 `failed` 终态，重复提交不会重新入队**——调用方拿到 `202 + status=failed` 后，需要触发重试只有两种途径：调用 `POST /api/admin/notifications/{id}/retry` 运维 API，或者用新的 `event_id` 提交一条全新的通知任务。

请求限制：

- 请求体最大由 `MAX_PAYLOAD_BYTES` 控制，默认 64 KB，超出返回 `413 payload_too_large`；
- `metadata` 最多 32 个字段；
- `metadata` 中字符串 value 最长 1024 字符。

## 供应商事件

| provider_code | event_type | payload 必填字段 |
|---|---|---|
| `crm` | `subscription_paid` | `email`、`subscription_id`、`amount`、`currency`、`paid_at` |
| `crm` | `user_registered` | `user_id`、`email`、`registered_at` |
| `ads` | `user_registered` | `user_id`、`registered_at` |
| `inventory` | `order_created` | `order_id`、`items`、`created_at` |

## 查询通知

`GET /api/notifications/{notification_id}`

返回当前状态、原始 payload、metadata、尝试次数和最后错误。

常见错误：

- `404 notification_not_found`：notification 不存在；
- `422 validation_error`：`notification_id` 不是 UUID。

## 运维 API

### Dashboard 指标

`GET /api/admin/metrics`

返回总数、按状态聚合、按供应商聚合和供应商列表。

### 供应商列表

`GET /api/admin/providers`

返回字段：

| 字段 | 说明 |
|---|---|
| `provider_code` | 供应商编码 |
| `display_name` | 展示名称 |
| `enabled` | 是否启用 |
| `paused` | 是否暂停接收新任务 |
| `queue_name` | 对应 worker 队列 |

### 暂停供应商

`POST /api/admin/providers/{provider_code}/pause`

暂停后只拒绝新建任务，已经入队或已经存在的任务不受影响。

成功响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "provider_code": "crm",
    "paused": true
  }
}
```

### 恢复供应商

`POST /api/admin/providers/{provider_code}/resume`

恢复后允许新建任务。

### 通知列表

`GET /api/admin/notifications`

Query 参数：

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---:|---|
| `provider_code` | string | - | 按供应商筛选 |
| `status` | string | - | 按通知状态筛选 |
| `limit` | integer | 20 | 每页数量，范围 `1..100` |
| `offset` | integer | 0 | 偏移量，必须 `>= 0` |

响应：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "total": 0,
    "limit": 20,
    "offset": 0
  }
}
```

### 通知详情

`GET /api/admin/notifications/{notification_id}`

比业务查询多返回 `attempts`，用于排查投递历史。

`attempts` 字段：

| 字段 | 说明 |
|---|---|
| `attempt_number` | 第几次投递 |
| `request_method` | 外部请求方法 |
| `request_url` | 外部请求 URL |
| `response_status` | 外部响应状态码 |
| `error_type` | 错误类型 |
| `error_message` | 错误信息 |
| `started_at` | 开始时间 |
| `finished_at` | 结束时间 |

### 人工重试

`POST /api/admin/notifications/{notification_id}/retry`

只有 `failed` 状态的任务可以人工重试。成功后任务状态会重新变为 `pending` 并再次入队。

## 错误码

| HTTP 状态 | code | 说明 |
|---:|---|---|
| 400 | `invalid_event` | provider 不支持该 event_type，或 payload 缺少供应商必填字段 |
| 401 | `unauthorized` | 缺少或错误的 `X-API-Key` |
| 404 | `provider_not_found` | provider 不存在 |
| 404 | `notification_not_found` | notification 不存在 |
| 409 | `provider_disabled` | provider 未启用 |
| 409 | `provider_paused` | provider 暂停接收新任务 |
| 409 | `notification_not_failed` | 只有 failed 任务可以人工重试 |
| 413 | `payload_too_large` | 请求体超过 `MAX_PAYLOAD_BYTES` |
| 422 | `validation_error` | 请求参数或请求体格式不合法 |
| 4xx | `http_error` | 路由不存在、方法不被允许等 FastAPI/Starlette 抛出的 HTTPException |
| 500 | `internal_error` | 未预期的服务端错误 |
| 503 | `enqueue_failed` | notification 已落库但入队失败，任务会被标记为 failed |

所有错误响应都遵循统一 `{code, message, data: null}` 结构。`code` 在成功时为整数 `0`、在错误时为字符串错误码，由 `app/errors.py` 中的全局 handler 兜底，调用方可以按 HTTP 状态码 + `code` 字段分支处理。
