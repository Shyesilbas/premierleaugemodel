"""
Premier League Model Engine — FastAPI Backend Server
Serves interactive prediction engine, fixtures, events, and static frontend dashboard.
"""

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from src.config import ROOT as BASE_DIR
from src.config import configure_logging

configure_logging()  # before the datasets load, so their progress is logged

from src.api import state  # noqa: E402  (loads datasets and models on import)
from src.api.etag import ETagMiddleware  # noqa: E402
from src.api.security import cors_origins  # noqa: E402
from src.api.routes import meta, teams, fixtures, players, matches, predict, stats  # noqa: E402

app = FastAPI(title="Premier League Model Engine API", version="1.0.0")

@app.middleware("http")
async def reload_changed_data(request: Request, call_next):
    path = request.url.path
    # Admin routes (including sync status polls) must not trigger mid-rebuild dataset reloads;
    # the finished sync job calls state.reload_runtime_datasets() once all rebuild steps complete.
    if path.startswith("/api/") and not path.startswith("/api/admin/") and not meta.is_sync_running():
        await run_in_threadpool(state._reload_if_data_changed)
    return await call_next(request)

app.add_middleware(ETagMiddleware)
# JSON payloads can reach several hundred KB (grouped fixtures, standings, compare directory);
# gzip reduces wire transfer size substantially.
app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"
FRONTEND_DIR = FRONTEND_DIST if FRONTEND_DIST.exists() else (BASE_DIR / "frontend")

for _module in (meta, teams, fixtures, players, matches, predict, stats):
    app.include_router(_module.router)

@app.get("/")
def root():
    return {
        "service": "Premier League Model Engine API",
        "status": "online",
        "frontend": "http://localhost:5173"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.server:app", host="127.0.0.1", port=8000, reload=True)
