from dataclasses import dataclass, field
from typing import Any


class ProviderAdapterError(ValueError):
    pass


@dataclass(frozen=True)
class AdapterRequest:
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    json: dict[str, Any] = field(default_factory=dict)


class ProviderAdapter:
    provider_code: str
    supported_event_types: set[str]

    def build_request(self, event_type: str, payload: dict[str, Any]) -> AdapterRequest:
        raise NotImplementedError

    def ensure_supported(self, event_type: str) -> None:
        if event_type not in self.supported_event_types:
            raise ProviderAdapterError(f"Unsupported event_type: {event_type}")

    def require_fields(self, payload: dict[str, Any], fields: set[str]) -> None:
        missing = sorted(field for field in fields if field not in payload)
        if missing:
            raise ProviderAdapterError(f"Missing required payload fields: {', '.join(missing)}")

    def is_success(self, status_code: int, body: bytes) -> bool:
        return 200 <= status_code < 300

