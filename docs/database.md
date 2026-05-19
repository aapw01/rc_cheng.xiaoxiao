# 数据库文档

## 核心表

| 表 | 用途 |
|---|---|
| `providers` | 供应商状态和队列分配 |
| `notifications` | 通知任务和业务事件 |
| `delivery_attempts` | 每次投递尝试 |
| `operator_actions` | 运维操作审计 |

## 关键约束

- `notifications(provider_code, event_type, event_id)` 唯一，保证内部幂等。
- `delivery_attempts(notification_id, attempt_number)` 唯一，保证尝试记录可审计。

## 状态

`notifications.status` 包含：

- `pending`
- `delivering`
- `retrying`
- `delivered`
- `failed`

