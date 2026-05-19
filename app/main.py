from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.api.admin import router as admin_router
from app.api.notifications import router as notifications_router
from app.errors import install_error_handlers

WEB_DIST_DIR = Path(__file__).resolve().parent.parent / "web" / "dist"
WEB_INDEX_FILE = WEB_DIST_DIR / "index.html"

app = FastAPI(title="API Notification Delivery Platform")
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
