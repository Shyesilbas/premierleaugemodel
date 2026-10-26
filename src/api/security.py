"""Admin access and CORS settings for the API.

``PLM_ADMIN_TOKEN``: when set (use an ASCII value, e.g. ``openssl rand -hex 24``), the admin routes
require it in the ``X-Admin-Token`` header.
Left unset (local development) they stay open and a warning is logged once.
``PLM_CORS_ORIGINS``: comma-separated browser origins allowed to call the API; the default is
the local dev servers. Same-origin traffic (Vite proxy, Caddy) does not need CORS at all.
"""

import logging
import os
import secrets

from fastapi import Header, HTTPException

logger = logging.getLogger("api_server")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173", "http://127.0.0.1:5173",
    "http://localhost:8080", "http://127.0.0.1:8080",
]


def cors_origins() -> list[str]:
    configured = [origin.strip() for origin in os.environ.get("PLM_CORS_ORIGINS", "").split(",") if origin.strip()]
    return configured or DEFAULT_CORS_ORIGINS


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency for the admin routes."""
    token = os.environ.get("PLM_ADMIN_TOKEN", "")
    if not token:
        return
    if not x_admin_token or not secrets.compare_digest(x_admin_token.encode(), token.encode()):
        raise HTTPException(status_code=401, detail="Admin token required")
