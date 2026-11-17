"""Conditional GET with content-hash ETags for read-only JSON API routes.

Every 200 response to read-only ``GET /api/*`` routes (excluding live admin/status
endpoints) gets a strong/weak blake2b content ETag and ``Cache-Control: no-cache``.
Browsers revalidate locally cached responses cleanly and receive a fast ``304 Not
Modified`` when the payload has not changed, while updated syncs/refreshes are never
served stale.
"""

from __future__ import annotations

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_EXCLUDED_PREFIXES = ("/api/admin/",)
_EXCLUDED_PATHS = ("/api/data-version",)


def _is_etag_eligible(request: Request) -> bool:
    if request.method != "GET":
        return False
    path = request.url.path
    if not path.startswith("/api/") or path in _EXCLUDED_PATHS:
        return False
    return not any(path.startswith(prefix) for prefix in _EXCLUDED_PREFIXES)


class ETagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.status_code != 200 or not _is_etag_eligible(request):
            return response

        body = b"".join([chunk async for chunk in response.body_iterator])
        etag = 'W/"' + hashlib.blake2b(body, digest_size=12).hexdigest() + '"'
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        headers["ETag"] = etag
        headers.setdefault("Cache-Control", "no-cache")

        client_tags = {tag.strip() for tag in request.headers.get("if-none-match", "").split(",") if tag.strip()}
        if etag in client_tags:
            headers.pop("content-type", None)
            return Response(status_code=304, headers=headers)

        return Response(content=body, status_code=200, headers=headers, media_type=None)
