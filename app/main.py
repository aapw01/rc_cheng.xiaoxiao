from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.notifications import router as notifications_router
from app.config import get_settings
from app.errors import error_response, install_error_handlers

WEB_DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
WEB_INDEX_FILE = WEB_DIST_DIR / "index.html"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    if settings.app_env == "production" and settings.api_key == "dev-api-key":
        raise RuntimeError("API_KEY must be configured in production")
    yield


app = FastAPI(title="API Notification Delivery Platform", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
async def ops_ui(path: str = "") -> HTMLResponse:
    if WEB_INDEX_FILE.exists():
        return HTMLResponse(WEB_INDEX_FILE.read_text(encoding="utf-8"))
    return HTMLResponse(
        "<!doctype html><html><head><title>Notification Ops</title></head>"
        "<body><div id=\"root\">Notification Ops UI is not built.</div></body></html>"
    )
