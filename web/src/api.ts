const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? window.location.origin;
const API_KEY = import.meta.env.VITE_API_KEY ?? "dev-api-key";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...(init?.headers ?? {})
    }
  });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.message ?? "Request failed");
  }
  return body.data as T;
}

export type Provider = {
  provider_code: string;
  display_name: string;
  enabled: boolean;
  paused: boolean;
  queue_name: string;
};

export type NotificationItem = {
  id: string;
  provider_code: string;
  event_type: string;
  event_id: string;
  status: string;
  attempt_count: number;
  last_error: string | null;
  payload: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type Attempt = {
  id: string;
  attempt_number: number;
  request_method: string | null;
  request_url: string | null;
  response_status: number | null;
  error_type: string | null;
  error_message: string | null;
  started_at: string;
  finished_at: string | null;
};

export type Metrics = {
  total: number;
  by_status: Record<string, number>;
  by_provider: Record<string, Record<string, number>>;
  providers: Provider[];
};

export function getMetrics() {
  return request<Metrics>("/api/admin/metrics");
}

export function getProviders() {
  return request<Provider[]>("/api/admin/providers");
}

export function pauseProvider(providerCode: string) {
  return request(`/api/admin/providers/${providerCode}/pause`, { method: "POST" });
}

export function resumeProvider(providerCode: string) {
  return request(`/api/admin/providers/${providerCode}/resume`, { method: "POST" });
}

export type NotificationList = {
  items: NotificationItem[];
  total: number;
  limit: number;
  offset: number;
};

export function getNotifications(params: { provider_code?: string; status?: string; limit?: number; offset?: number }) {
  const search = new URLSearchParams();
  if (params.provider_code) search.set("provider_code", params.provider_code);
  if (params.status) search.set("status", params.status);
  if (params.limit) search.set("limit", String(params.limit));
  if (params.offset) search.set("offset", String(params.offset));
  return request<NotificationList>(`/api/admin/notifications?${search}`);
}

export function getNotification(id: string) {
  return request<NotificationItem & { attempts: Attempt[] }>(`/api/admin/notifications/${id}`);
}

export function retryNotification(id: string) {
  return request(`/api/admin/notifications/${id}/retry`, { method: "POST" });
}
