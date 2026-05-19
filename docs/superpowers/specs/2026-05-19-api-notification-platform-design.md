# API 通知投递平台设计

> 本文档是给 AI coding 工具的实现 spec，定义**做什么、不做什么、怎么做**。`AI_USAGE.md` 和外层评审 README 不在本文档范畴。

## 1. 目标

实现一个企业内部 API 通知投递平台：在业务系统发生关键事件后，异步、可靠地通知外部供应商 HTTP API。

平台接收业务事件，转换为不同供应商要求的 HTTP 请求格式，异步投递到目标系统，记录每次投递尝试，失败后重试，并提供一个简单的运维管理页面用于查看状态和人工处理。

## 2. 产品形态

这个系统定位为“供应商适配型通知平台”，不是透明 HTTP 代理。

业务系统提交的是业务事件，例如：

```json
{
  "provider_code": "crm",
  "event_type": "subscription_paid",
  "event_id": "sub_paid_202605190001",
  "occurred_at": "2026-05-19T10:00:00Z",
  "payload": {
    "user_id": "u_123",
    "email": "a@example.com",
    "subscription_id": "sub_001",
    "amount": 19900,
    "currency": "USD"
  },
  "metadata": {
    "source_system": "billing",
    "trace_id": "trace_abc123",
    "priority": "normal"
  }
}
```

通知平台负责校验事件、保存任务、根据 `provider_code + event_type` 选择供应商适配器、构造外部 HTTP 请求，并通过后台 worker 投递。

业务系统不直接提交供应商 URL、供应商 Header 或供应商格式的 Body。这些供应商协议细节由通知平台内部的 adapter 管理，避免供应商 API 变化扩散到多个业务系统。

## 3. 对外 API 核心字段

`provider_code` 表示要通知哪个下游供应商，例如 `crm`、`ads`、`inventory`。

`event_type` 表示发生了什么业务事件，例如 `user_registered`、`subscription_paid`、`order_created`。它用于选择 payload schema 和供应商 adapter 的转换逻辑。

`event_id` 是业务事件的唯一 ID。平台会对 `provider_code + event_type + event_id` 建唯一约束，保证业务系统重复提交同一事件时不会创建多条通知任务。

`payload` 是业务事件数据，不是供应商请求数据。平台会保存原始 payload，并在 adapter 转换之前做基础 schema 校验。

`metadata` 是运维和链路追踪上下文，例如来源系统、trace ID、请求人、业务线、优先级等。它不参与供应商请求协议转换，主要用于排查问题、关联日志、展示来源和保留审计信息。

典型用途：

- `source_system`：说明事件来自哪个内部系统，例如 billing、user-center、order-service；
- `trace_id`：关联业务系统日志、通知平台日志和 worker 投递日志；
- `requested_by`：记录触发方，方便审计；
- `priority`：第一版只展示，不做复杂优先级调度；
- 其他业务上下文：例如 region、tenant、campaign 等，便于运维筛选和排查。

## 4. 第一版实现范围

- FastAPI 后端，提供通知提交 API 和运维 API。
- Python 项目使用 uv 管理依赖、虚拟环境和运行命令。
- PostgreSQL 持久化供应商状态、通知任务和投递尝试记录。
- 数据库 schema 变更使用 Alembic 管理迁移。
- Redis + Dramatiq 作为异步消息队列和后台任务执行框架。
- httpx 执行外部 HTTP 请求。
- `web/` 目录下实现 React/Vite 运维管理页面，使用轻量 React 组件库提升交付效率。
- Docker Compose 支持一键启动本地完整环境。
- 供应商 adapter 抽象，并提供几个示例供应商和 AI-ready 扩展模板。
- 采用至少一次投递语义。
- 平台内部保证任务幂等。
- 重试策略只暴露一个环境变量：`DEFAULT_MAX_ATTEMPTS`。
- 运维页面支持供应商暂停/恢复。
- 运维页面支持失败任务人工重试。
- pytest 覆盖 API、adapter 转换、重试决策、worker 幂等和关键集成流程。
- 提供 README、API 文档、数据库文档、部署文档、架构文档、测试文档和 AI 使用说明。
- 提供供应商接入文档，说明如何使用 AI coding 工具快速扩展新供应商。
- 供应商认证凭证（API key、Bearer token 等）通过环境变量管理。第一版不引入 secret manager、密钥加密存储或密钥轮转，命名约定和示例见 `docs/provider-onboarding.md`。

## 5. 第一版明确不做

- 不做供应商新增或编辑页面。
- 不做供应商 endpoint/header/body 配置热更新。
- 不做面向非开发人员的请求模板 DSL。
- 不承诺对外部非幂等供应商 API 做 exactly-once 投递。
- 不做多租户权限系统或复杂 RBAC。
- 不做完整告警系统、分页监控系统或长期指标存储。
- 不引入 Kafka、Celery 或复杂任务编排。
- 不做复杂工作流 DAG 或营销活动调度。

## 6. 整体架构

```text
业务系统
  -> FastAPI API
  -> PostgreSQL 创建通知任务
  -> Dramatiq actor 入队
  -> Redis broker / queue
  -> Dramatiq worker 消费任务
  -> Provider adapter 构造供应商请求
  -> httpx 发送外部 HTTP 请求
  -> 外部供应商 API

React 运维管理页面
  -> FastAPI admin API
  -> PostgreSQL / Redis 聚合出的状态和指标
```

运行时服务：

- `api`：FastAPI 后端服务。
- `worker`：Dramatiq 后台投递 worker。
- `postgres`：持久化数据库。
- `redis`：消息队列 broker。
- `web`：React 运维管理页面。

## 7. 供应商 Adapter 模型

供应商 HTTP 协议细节放在代码 adapter 中：

```text
app/providers/
  base.py
  registry.py
  adapters/
    ads.py
    crm.py
    inventory.py
    generic_webhook.py
```

每个 adapter 负责定义：

- 支持的 `provider_code`；
- 支持的 `event_type`；
- 事件 payload schema；
- URL 构造方式；
- HTTP method；
- headers；
- body 转换逻辑；
- 哪些 HTTP 状态码算成功。

新增一个供应商时，预期流程是：

1. 新增一个 adapter 文件；
2. 在 provider registry 中注册；
3. 定义支持的事件类型和 payload schema；
4. 增加 provider 种子数据；
5. 增加 adapter 和投递测试。

第一版使用 typed Python adapter，**不要**实现请求模板 DSL，也**不要**预留 DSL 扩展接口。

完整的接入流程、adapter 模板、payload schema 模板、seed 数据示例、测试模板、信息清单和不同供应商类型的接入指导见独立文档 `docs/provider-onboarding.md`。

## 8. 队列策略

系统通过 `provider.queue_name` 支持供应商队列分配。

第一版给示例供应商配置独立队列：

```text
notifications_crm
notifications_ads
notifications_inventory
```

这样一个供应商长期失败时，不会阻塞其他供应商的任务消费，也更容易观察某个供应商的堆积情况。

实现上，`provider.queue_name` 不是只用于展示，而是实际入队路由依据。

Dramatiq 的常规 actor queue 通常在 actor 声明时固定。为了避免第一版实现动态修改 actor queue，采用更简单稳定的队列路由方式：

- 每个第一版示例队列声明一个轻量 actor，例如 `deliver_crm_notification`、`deliver_ads_notification`、`deliver_inventory_notification`；
- 这些 actor 只负责绑定不同的 `queue_name`，内部都调用同一个 `deliver_notification(notification_id)` 业务函数；
- API 创建 notification 后，根据 provider 配置选择对应 actor 入队；
- worker 启动时监听第一版支持的固定队列列表。

第一版**不要**做运行时动态新增队列。新增供应商后，需要新增对应 actor 或把供应商映射到已有队列池，并重启 worker。

## 9. 可靠性语义

平台采用至少一次投递。

只有供应商返回成功状态码时才认为投递成功，默认规则是任意 `2xx` 状态码算成功。

以下情况都视为投递失败：

- 非成功 HTTP 状态码；
- 连接错误；
- 请求超时；
- DNS 或 TLS 错误；
- adapter 转换失败。

失败时，worker 会记录一次投递尝试，并根据剩余尝试次数决定是否重试；如果达到最大尝试次数，则标记为 `failed`。

第一版不实现 `uncertain` 状态。只要没有明确成功，就按失败处理并进入重试流程。

worker 投递必须有超时保护，避免外部供应商长时间不响应导致 worker 被一个慢请求长时间占用。

第一版只使用 httpx 请求超时：通过 `HTTP_REQUEST_TIMEOUT_SECONDS` 控制（默认 10 秒）。覆盖 connect、read、write 全过程，超时时 httpx 会抛出超时异常，被 worker 捕获后按失败处理。

第一版**不要**使用 Dramatiq actor `time_limit` 强制中止任务。原因是强制中止可能让应用层没有机会写入 `delivery_attempts` 或恢复 `notifications` 状态，反而引入 `delivering` 卡死任务。后续如果需要 actor 级别超时，需要同时实现 stale delivering recovery。

httpx 超时会记录一次失败的 `delivery_attempts`（错误类型标为 `timeout`），然后按正常重试流程进入下一次尝试。

Dramatiq 负责消息级重试调度，但通知平台仍然需要把每次投递尝试写入 `delivery_attempts`。原因是 Dramatiq 的失败重试信息主要服务于队列执行，不适合作为业务审计和运维查询的唯一来源。运维 UI 需要展示每次尝试的外部请求摘要、响应状态码、错误类型、错误信息和时间；这些数据必须持久化到 PostgreSQL。

## 10. 下游 API 非幂等时的处理边界

本设计假设外部供应商 API 可能都是非幂等的。

平台能保证的是“内部任务处理幂等”，不能保证“外部供应商副作用 exactly-once”。

内部幂等规则：

- `provider_code + event_type + event_id` 唯一；
- 重复提交同一业务事件时返回已有 notification，不创建重复任务；
- 已经成功的任务不会被自动重复投递；
- worker 投递前会检查数据库中的任务状态；
- 同一个 notification 同一时间最多只有一个活跃投递流程；
- 每次投递尝试都会记录，方便审计和排查。

worker 开始投递前需要先在数据库中抢占任务，避免重复消息或并发 worker 导致重复投递。第一版采用事务内条件更新：只有状态为 `pending` 或 `retrying` 的任务才能更新为 `delivering`。如果更新不到记录，说明任务已经被其他 worker 处理或处于终态，当前 actor 直接结束。

外部限制：

如果供应商已经处理成功，但响应在网络中丢失或超时，平台无法知道外部副作用是否已经发生。由于第一版采用至少一次投递，后续重试可能导致供应商侧重复处理。这是已接受的边界，**不要**尝试通过对账、查询接口或 `uncertain` 状态机制规避它。

## 11. 重试策略

第一版只暴露一个重试配置：

```text
DEFAULT_MAX_ATTEMPTS=6
```

规则：

- `DEFAULT_MAX_ATTEMPTS > 0`：最多尝试 N 次，之后进入 `failed`。
- `DEFAULT_MAX_ATTEMPTS = 1`：只投递一次，不自动重试。
- `DEFAULT_MAX_ATTEMPTS = -1`：无限重试。

Dramatiq 的 `max_retries` 表示失败后的重试次数，而这里的 `DEFAULT_MAX_ATTEMPTS` 表示总投递尝试次数。因此实现时需要做映射：

```text
dramatiq_max_retries = DEFAULT_MAX_ATTEMPTS - 1
```

当 `DEFAULT_MAX_ATTEMPTS = -1` 时，Dramatiq actor 配置为不限制重试次数。

退避策略由系统内置，不在 UI 或 provider 配置中暴露：

```text
delay_seconds = min(60 * 2^(attempt_number - 1), 3600)
```

也就是 1 分钟、2 分钟、4 分钟、8 分钟、16 分钟、32 分钟，之后最多每 60 分钟重试一次。

系统通过以下方式降低长期失败供应商带来的影响：

- 指数退避，避免高频打爆下游；
- 供应商队列隔离；
- 供应商暂停/恢复；
- 达到最大尝试次数后进入 `failed`；
- metrics 和 UI 暴露堆积与失败原因。

### 11.1 重试配置硬约束

- 重试配置在第一版**只有 `DEFAULT_MAX_ATTEMPTS` 这一个全局变量**。**不要**在数据库里加 provider 维度的 `max_attempts` 字段，**不要**让退避公式可配置；
- 少数供应商如果有"特定错误不应重试"的需求，由 adapter 在 `is_success` 或异常映射中把这类错误标为 `non_retryable`，让 Dramatiq middleware 直接放弃重试，**不要**通过配置层解决；
- `DEFAULT_MAX_ATTEMPTS` 的三种语义覆盖典型运维需求：`>0` = 有限重试 N 次后 `failed`、`=1` = 只投一次不重试、`=-1` = 无限重试。

## 12. 供应商运维操作

供应商记录包含：

- `provider_code`；
- 展示名称；
- `enabled`；
- `paused`；
- `queue_name`。

第一版 UI 支持：

- 查看供应商状态；
- 暂停供应商投递；
- 恢复供应商投递。

行为规则：

- 重复提交优先于 provider 状态检查：如果相同 `provider_code + event_type + event_id` 已经存在，API 直接返回已有 notification，状态码 `202`；
- 只有创建新 notification 时才检查 provider 是否 `paused` 或 `enabled=false`；
- 当供应商 `paused=true` 时，新提交到该供应商的通知在 API 入口被拒绝（`409 Conflict`，错误码 `provider_paused`）；
- 已经进入 Redis 队列或已经开始投递的任务**不要**做特殊拦截，继续按正常失败、重试和最终 `failed` 规则处理；
- **不要**引入额外的 `paused` 任务状态、**不要**实现"暂停时把队列内任务批量转 paused、恢复时批量重新入队"的机制；
- 当供应商 `enabled=false` 时，新提交到该供应商的通知同样被拒绝（错误码 `provider_disabled`）；
- 第一版 UI **不要**做新增或编辑供应商 endpoint、headers、body 等协议配置的能力。

### 12.1 后续版本 TODO：自动熔断与自动恢复探测

第一版**不要**实现自动熔断、自动暂停、自动恢复探测，也**不要**增加 `AUTO_PAUSE_*` 相关环境变量。

后续版本可以考虑：

- 按供应商统计滚动窗口失败率；
- 达到阈值后自动暂停供应商；
- 通过独立健康检查 endpoint 或供应商只读接口做恢复探测；
- 区分人工暂停和系统自动暂停；
- 记录自动暂停和自动恢复的 operator action。

注意：不要用真实非幂等业务通知任务做自动探测，否则可能制造额外重复副作用。

## 13. 通知任务状态

预期状态：

- `pending`：任务已创建，等待投递。
- `delivering`：worker 正在投递。
- `retrying`：投递失败，等待下一次重试。
- `delivered`：供应商返回成功。
- `failed`：达到最大尝试次数或被人工标记失败。

人工重试会把 `failed` 任务重新置为 `pending` 并再次入队。

## 14. 运维管理页面

`web/` 下实现一个轻量 React 运维管理页面。

页面包括：

- Dashboard：按状态统计总量、最近失败、队列堆积概览。
- Providers：供应商列表、启用状态、暂停状态、队列名、暂停/恢复操作。
- Notifications：通知任务列表，支持按供应商和状态筛选。
- Notification Detail：查看 payload、metadata、当前状态、投递尝试历史和最后错误。

UI 定位是内部运维工具，强调清晰、可扫描、能操作，不做营销页或复杂后台系统。

## 15. API 范围

业务系统 API：

- `POST /api/notifications`：提交业务事件。
- `GET /api/notifications/{id}`：查询通知任务状态。

运维 API：

- `GET /api/admin/metrics`：Dashboard 指标。
- `GET /api/admin/providers`：供应商列表。
- `POST /api/admin/providers/{provider_code}/pause`：暂停供应商投递。
- `POST /api/admin/providers/{provider_code}/resume`：恢复供应商投递。
- `GET /api/admin/notifications`：按条件查询通知任务。
- `GET /api/admin/notifications/{id}`：查看通知详情。
- `POST /api/admin/notifications/{id}/retry`：人工重试失败任务。

辅助 API：

- `GET /health`：健康检查。

第一版所有业务 API 和运维 API 使用简单 API Key Header 鉴权。

### 15.1 业务 API 提交语义

`POST /api/notifications` 的返回职责是"让调用方明确知道这次提交是成功还是失败"，但**不承诺通知最终是否送达**。

- 成功入队：返回 `202 Accepted`，body 包含 `notification_id` 和当前状态（首次提交时为 `pending`，重复提交时为已有任务的状态）。调用方拿到 2xx 即可认为通知平台已经接管这次事件；
- 重复提交：相同 `provider_code + event_type + event_id` 会命中唯一约束，平台返回已有 `notification_id`，状态码仍是 `202`。这是平台幂等保证的一部分，调用方不需要做去重；
- 校验失败：4xx（缺字段、未知 provider、未知 event_type、payload schema 不匹配、供应商 `paused` 或 `disabled` 等）；
- 入队失败：5xx（数据库不可写、Redis 不可用等基础设施故障）。调用方可以按自己的策略重试，重复 POST 同一 `event_id` 安全。

简而言之：业务侧通过 HTTP 状态码区分"我提交了 vs 提交失败"，**不需要、也无法在这个返回里得到"通知是否成功送达"的结果**。

### 15.2 业务侧如何拿到最终投递结果

业务侧拿最终投递结果**只有一种方式**：用 `POST /api/notifications` 返回的 `notification_id` 去轮询 `GET /api/notifications/{id}`，任务进入终态（`delivered` 或 `failed`）即视为投递结束。

第一版**不要**做反向 webhook 回调、SSE、WebSocket 推送或任何主动通知业务方的能力，也**不要**在 `notifications` 表里预留 `callback_url` 之类的字段。

### 15.3 输入限制与脱敏

- payload 限制：单个 `POST /api/notifications` 请求体最大 `64 KB`（由 `MAX_PAYLOAD_BYTES` 配置）。超出直接 `413 Payload Too Large`。这个值覆盖目前所有示例供应商的事件，并避免大对象长期沉淀在数据库；
- metadata 字段数和单字段长度限制做基础校验（例如 `metadata` 字段数 ≤ 32、每个 value 字符串 ≤ 1 KB），具体阈值由 schema 校验层固定；
- 日志记录：每次提交、入队、投递尝试都会写结构化日志，包含 `notification_id`、`provider_code`、`event_type`、`trace_id` 等；
- 脱敏：第一版只对日志输出层做最朴素的脱敏（已知敏感字段名命中白名单——如 `email`、`phone`、`id_card`——按"邮箱保留前缀 + 末 4 位掩码"等固定规则处理）。字段路径配置、自定义脱敏规则、敏感字段自动识别属于后续版本能力，第一版不做。落库时 `payload` 仍按原样保留，便于运维排查，敏感度通过数据库访问权限控制。

## 16. 数据模型

核心表：

`providers`

- 供应商身份；
- 运维状态；
- 队列分配。

`notifications`

- provider code；
- event type；
- event ID；
- 原始 payload；
- metadata；
- 状态；
- 尝试次数；
- 创建和更新时间。

`delivery_attempts`

- notification ID；
- 第几次尝试；
- 外部请求摘要；
- 响应状态码；
- 错误类型；
- 错误信息；
- 开始和结束时间。

`operator_actions`

- 操作类型；
- 目标资源；
- 操作前状态；
- 操作后状态；
- 操作人；
- 操作时间。

关键索引：

- `notifications(provider_code, event_type, event_id)` 唯一索引；
- `notifications(provider_code, status)` 用于供应商维度堆积统计和运维筛选；
- `notifications(status, updated_at)` 用于按状态时间排序的运维列表；
- `delivery_attempts(notification_id, attempt_number)` 用于查看投递历史。

## 17. 测试策略

测试覆盖：

- 提交合法通知；
- 重复提交同一事件时返回已有 notification；
- 未知 provider 或 event type 被拒绝；
- adapter 能把业务 payload 转成供应商请求；
- 成功投递后任务变为 `delivered`；
- 失败投递会增加尝试次数并安排重试；
- 达到最大尝试次数后任务变为 `failed`；
- `DEFAULT_MAX_ATTEMPTS=-1` 时持续重试；
- 供应商暂停后拒绝新的通知提交；
- 人工重试会把 failed 任务重新入队；
- admin metrics 能正确聚合状态。

单元测试中 mock 外部 HTTP 请求。Docker Compose 用于本地集成验证。

仓库需要提供 `docs/testing.md`，明确说明：

- 如何运行全部测试；
- 如何只运行后端单元测试；
- 如何只运行前端测试；
- 如何启动 Docker Compose 运行集成测试；
- 集成测试依赖哪些服务，例如 Postgres、Redis、API、worker；
- 如何验证 Dramatiq worker 能消费任务；
- 如何验证失败重试、达到最大次数进入 `failed`、人工重试重新入队；
- 如何用 mock vendor server 验证外部 HTTP 投递；
- CI 中推荐执行哪些测试。

集成测试建议覆盖：

- API 创建 notification 后，worker 能消费并投递到 mock vendor；
- mock vendor 返回 `2xx` 时任务进入 `delivered`；
- mock vendor 返回 `500` 时任务进入 `retrying` 或最终 `failed`；
- 重复提交同一 `provider_code + event_type + event_id` 不产生重复任务；
- 暂停供应商后新提交被拒绝，恢复后可以重新提交；
- failed 任务通过 admin API 人工重试后重新入队；
- React 页面能从 API 读取 metrics、providers 和 notifications 数据。

## 18. 已确认的实现决策

- Python 包和依赖使用 uv 管理；
- 数据库迁移使用 Alembic；
- React 运维页面使用轻量组件库（如 Ant Design / MUI / shadcn/ui 任选其一），**不要**从零实现基础控件；
- worker 重试调度使用 Dramatiq Retries middleware：消息级重试、退避和最终放弃交给 middleware，应用层负责在每次投递前后更新 `notifications` 和 `delivery_attempts`；
- 应用层**不要**保留 `next_retry_at` 字段。任务下次会在什么时候被重试完全由 Dramatiq 调度决定，**不要**在数据库里冗余存储。

## 19. 可观测性（第一版 TODO）

第一版**不要**引入完整可观测性栈：**不要**集成 Prometheus、OpenTelemetry、Sentry、Grafana，**不要**实现 `/metrics` 端点，**不要**做告警通道。

第一版只做：

- API 和 worker 输出常规日志，请求级日志至少包含 `notification_id`、`provider_code`、`event_type`、`trace_id`、`attempt_number` 这几个字段；
- 运维管理页面承担"看现在系统怎么样"的功能（堆积、失败、最近一次错误等）；
- `delivery_attempts` 表作为审计来源，运维通过 SQL 直接查。

下列项目作为 TODO 留给后续版本，**第一版不要做**：

- 统一结构化 JSON 日志格式 + trace_id 全链路透传；
- `/metrics` 端点和 `notifications_total{status, provider}` / `delivery_attempts_total{result, provider}` / `auto_pause_events_total{provider}` / `queue_depth{queue}` 等业务指标；
- worker actor 执行时长、外部 HTTP 调用耗时分布等基础设施指标；
- OpenTelemetry SDK 和 OTLP exporter；
- Sentry/Rollbar 类错误聚合；
- 自动暂停事件、`failed` 任务突增、队列长时间堆积等告警；
- Grafana 仪表板。
