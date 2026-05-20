import hashlib
import hmac
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.notifications import router as notifications_router
from app.config import get_settings
from app.errors import error_response, install_error_handlers

WEB_DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
WEB_INDEX_FILE = WEB_DIST_DIR / "index.html"
OPS_SESSION_COOKIE = "ops_session"


PRODUCTION_SENTINEL_VALUES = {
    "API_KEY": "dev-api-key",
    "PROVIDER_CRM_API_KEY": "dev-crm-key",
    "PROVIDER_ADS_BEARER_TOKEN": "dev-ads-token",
    "PROVIDER_INVENTORY_API_KEY": "dev-inventory-key",
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.app_env == "production":
        for env_name, sentinel in PRODUCTION_SENTINEL_VALUES.items():
            if getattr(settings, env_name.lower()) == sentinel:
                raise RuntimeError(f"{env_name} must be configured in production")
    yield


app = FastAPI(title="API Notification Delivery Platform", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().effective_cors_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)
app.include_router(notifications_router)
app.include_router(admin_router)

if WEB_DIST_DIR.exists():
    app.mount("/ops/assets", StaticFiles(directory=WEB_DIST_DIR / "assets"), name="ops-assets")


@app.middleware("http")
async def reject_oversized_notification_payloads(request: Request, call_next):
    if request.method == "POST" and request.url.path == "/api/notifications":
        content_length = request.headers.get("content-length")
        if (
            content_length is not None
            and content_length.isdigit()
            and int(content_length) > get_settings().max_payload_bytes
        ):
            return error_response(413, "payload_too_large", "Request body is too large")
    return await call_next(request)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ops", include_in_schema=False)
@app.get("/ops/{path:path}", include_in_schema=False)
async def ops_ui(request: Request, path: str = "") -> HTMLResponse:
    if path == "login":
        return ops_login_page()
    if request.cookies.get(OPS_SESSION_COOKIE) != ops_session_token():
        return ops_login_page(status_code=401)
    if WEB_INDEX_FILE.exists():
        return HTMLResponse(WEB_INDEX_FILE.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!doctype html><html lang=\"zh-CN\"><head><title>通知投递运维</title></head>"
        "<body><div id=\"root\">运维 UI 尚未构建。</div></body></html>"
    )


@app.post("/ops/login", include_in_schema=False)
async def ops_login(request: Request) -> Response:
    form = parse_qs((await request.body()).decode("utf-8"))
    password = form.get("password", [""])[0]
    if not secrets.compare_digest(password, get_settings().ops_password):
        return ops_login_page(status_code=401, error="密码不正确")
    response = RedirectResponse("/ops", status_code=303)
    response.set_cookie(
        OPS_SESSION_COOKIE,
        ops_session_token(),
        httponly=True,
        samesite="lax",
        secure=get_settings().app_env == "production",
    )
    return response


def ops_session_token() -> str:
    digest = hmac.new(get_settings().ops_password.encode("utf-8"), b"ops-session", hashlib.sha256).hexdigest()
    return f"ops:{digest}"


def ops_login_page(status_code: int = 200, error: str | None = None) -> HTMLResponse:
    error_html = f"<p class=\"error\">{error}</p>" if error else ""
    return HTMLResponse(
        f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>运维登录</title>
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f3f4f6;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      width: min(360px, calc(100vw - 40px));
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 8px;
      padding: 28px;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
    }}
    h1 {{ margin: 0 0 20px; font-size: 22px; }}
    label {{ display: block; margin-bottom: 8px; color: #4b5563; }}
    input {{
      width: 100%;
      box-sizing: border-box;
      height: 40px;
      border: 1px solid #d1d5db;
      border-radius: 6px;
      padding: 0 12px;
      font-size: 15px;
    }}
    button {{
      width: 100%;
      height: 40px;
      margin-top: 16px;
      border: 0;
      border-radius: 6px;
      background: #111827;
      color: #fff;
      font-weight: 600;
      cursor: pointer;
    }}
    .error {{ margin: 0 0 12px; color: #b91c1c; }}
  </style>
</head>
<body>
  <main>
    <h1>运维登录</h1>
    {error_html}
    <form method="post" action="/ops/login">
      <label for="password">运维密码</label>
      <input id="password" name="password" type="password" autocomplete="current-password" autofocus />
      <button type="submit">进入控制台</button>
    </form>
  </main>
</body>
</html>
""",
        status_code=status_code,
    )
