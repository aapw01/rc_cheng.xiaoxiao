# 供应商接入文档

本文说明如何在 API 通知投递平台中新增一个供应商。流程被刻意设计为对 AI coding 工具友好：只要用户准备好下面"信息清单"，AI 就能按本文档生成 adapter、payload schema、provider seed 数据和测试。

## 1. 接入概览

新增一个供应商的步骤：

1. 在 `app/providers/adapters/` 下新增一个 adapter 文件；
2. 在 `app/providers/registry.py` 中注册；
3. 定义支持的 `event_type` 和对应的 payload schema；
4. 增加 provider seed 数据（队列名、展示名等）；
5. 增加 adapter 单元测试和投递集成测试；
6. 通过环境变量提供供应商认证凭证。

详细模板和示例见后续章节。

## 2. 用户需要提供的信息清单

接入一个新供应商前，需要先准备好以下信息：

- 供应商名称和 `provider_code`（短标识，例如 `crm`、`ads`、`inventory`）；
- 支持的业务事件类型，例如 `user_registered`、`subscription_paid`；
- 每种事件的业务 payload 字段含义和必填项；
- 供应商 API endpoint、HTTP method、认证方式和 headers；
- 供应商请求 body 示例；
- 成功状态码规则（默认 `2xx` 算成功，特殊规则需要单独说明）；
- 失败响应示例；
- 是否有频率限制、超时建议或特殊错误码；
- 是否允许重复调用（第一版默认按非幂等下游处理）；
- 供应商认证凭证的环境变量命名建议，例如 `PROVIDER_CRM_API_KEY`。

## 3. 不同供应商类型的接入指导

不同供应商在协议上差异较大，按下面几种类型选择 adapter 模板：

- **简单 webhook 型**：一个事件对应一个 HTTP endpoint，只需要 adapter 做字段映射；
- **多事件单供应商型**：同一供应商支持多个 `event_type`，adapter 内按事件选择不同转换逻辑；
- **认证复杂型**：需要 API key、Bearer token 或签名 headers，adapter 负责统一封装；
- **字段转换复杂型**：供应商字段命名、时间格式、金额单位和枚举值与内部事件不同，adapter 负责转换；
- **多 endpoint 型**：同一供应商不同事件打到不同 URL，adapter 根据 `event_type` 选择 endpoint。

如果用户提供的信息不能明确判断属于哪种类型，AI 应回到信息清单确认，避免做出错误假设。

## 4. Adapter 文件模板

```python
# app/providers/adapters/example.py
from app.providers.base import ProviderAdapter, AdapterRequest


class ExampleAdapter(ProviderAdapter):
    provider_code = "example"
    supported_event_types = {"user_registered", "subscription_paid"}

    def build_request(self, event_type: str, payload: dict) -> AdapterRequest:
        if event_type == "user_registered":
            return AdapterRequest(
                method="POST",
                url=f"{self.base_url}/users",
                headers=self.auth_headers(),
                json={
                    "id": payload["user_id"],
                    "email": payload["email"],
                },
            )
        if event_type == "subscription_paid":
            return AdapterRequest(
                method="POST",
                url=f"{self.base_url}/subscriptions/{payload['subscription_id']}/paid",
                headers=self.auth_headers(),
                json={
                    "amount_cents": payload["amount"],
                    "currency": payload["currency"],
                },
            )
        raise ValueError(f"Unsupported event_type: {event_type}")

    def is_success(self, status_code: int, body: bytes) -> bool:
        return 200 <= status_code < 300
```

## 5. Payload Schema 模板

每个 `event_type` 都需要一份 schema，平台会在 adapter 转换前做基础校验：

```python
# app/providers/adapters/example_schemas.py
EXAMPLE_SCHEMAS = {
    "user_registered": {
        "type": "object",
        "required": ["user_id", "email"],
        "properties": {
            "user_id": {"type": "string"},
            "email": {"type": "string", "format": "email"},
        },
        "additionalProperties": True,
    },
    "subscription_paid": {
        "type": "object",
        "required": ["subscription_id", "amount", "currency"],
        "properties": {
            "subscription_id": {"type": "string"},
            "amount": {"type": "integer", "minimum": 0},
            "currency": {"type": "string"},
        },
        "additionalProperties": True,
    },
}
```

## 6. Provider Registry 注册

```python
# app/providers/registry.py
from app.providers.adapters.example import ExampleAdapter

PROVIDERS = {
    ExampleAdapter.provider_code: ExampleAdapter,
}
```

## 7. Provider Seed 数据示例

种子数据通过独立 seed 脚本写入 `providers` 表，可重复执行：

```python
# scripts/seed_providers.py
PROVIDER_SEEDS = [
    {
        "provider_code": "example",
        "display_name": "Example Provider",
        "queue_name": "notifications_example",
        "enabled": True,
        "paused": False,
    },
]
```

新增供应商后，运行 seed 脚本插入 `providers` 记录（`enabled=true`、独立的 `queue_name`），然后**重启 worker**。`scripts/run_worker.py` 启动时会从 DB 重新读取 enabled queue 列表并自动注册对应 actor，**不需要**在代码里手动加 actor 定义。第一版不支持运行时动态新增队列（设计文档第 8 节）。

## 8. 供应商认证凭证

第一版认证凭证全部通过环境变量管理。命名约定：

```text
PROVIDER_<PROVIDER_CODE>_API_KEY
PROVIDER_<PROVIDER_CODE>_BEARER_TOKEN
PROVIDER_<PROVIDER_CODE>_SECRET
```

例如 `PROVIDER_CRM_API_KEY`、`PROVIDER_ADS_BEARER_TOKEN`。

Adapter 在初始化时读取对应环境变量，组装到请求 headers 中。Docker Compose 在 `.env` 中统一管理。第一版不做密钥存储加密、密钥轮转和 secret manager 集成，这些是未来演进项。

## 9. 测试模板

每个新供应商至少需要两类测试：

**adapter 单元测试**：

```python
# tests/providers/test_example_adapter.py
def test_user_registered_request():
    adapter = ExampleAdapter(base_url="https://example.test", api_key="k")
    req = adapter.build_request("user_registered", {
        "user_id": "u_1",
        "email": "a@example.com",
    })
    assert req.method == "POST"
    assert req.url == "https://example.test/users"
    assert req.json["email"] == "a@example.com"
```

**端到端集成测试**：使用 mock vendor server，覆盖：

- 成功投递（mock 返回 200，任务进入 `delivered`）；
- 失败投递（mock 返回 500，任务进入 `retrying`，达到最大次数后 `failed`）；
- 重复提交同一 `event_id` 不创建重复任务。

## 10. 本地验证命令

```bash
uv run pytest tests/providers/test_example_adapter.py
uv run python -m scripts.seed_providers
docker compose up --build -d
uv run pytest tests/integration/test_example_delivery.py
```

通过本地验证后，新供应商接入完成。

## 11. 第一版边界

本文档对应平台第一版的供应商接入流程。以下能力第一版不提供：

- 在运维 UI 上新增/编辑供应商；
- 供应商 endpoint、headers、body 模板的运行时热更新；
- 非开发人员维护的请求模板 DSL；
- 加密密钥存储和 secret manager 集成。

未来如果供应商接入非常频繁，可以再演进为配置化 DSL 或后台编辑界面。
