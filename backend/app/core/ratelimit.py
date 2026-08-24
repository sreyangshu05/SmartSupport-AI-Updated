"""In-memory sliding-window rate limiting applied via FastAPI middleware.

Chosen to be dependency-free and fail open: if memory/state is unavailable the
limiter simply allows the request through, which matches the application's
"degrade gracefully" posture. It is intended as a first line of defense.

Limits are expressed as ``(max_requests, window_seconds)``. The default global
limit is permissive while auth endpoints get a strict limit to blunt credential
stuffing at the source.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from app.core.config import get_settings

# (max_requests, window_seconds) per scope.
DEFAULT_LIMIT: tuple[int, int] = (300, 60)           # general API
AUTH_LIMIT: tuple[int, int] = (10, 60)               # /api/auth/login|register
AUTH_PATHS = {"/api/auth/login", "/api/auth/register"}


class _SlidingWindowLimiter:
    """Thread-safe per-key sliding-window counter (deque of hit timestamps)."""

    def __init__(self) -> None:
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: tuple[int, int]) -> bool:
        max_requests, window = limit
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            # Drop hits older than the window.
            cutoff = now - window
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= max_requests:
                return False
            bucket.append(now)
            return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._limiter = _SlidingWindowLimiter()
        settings = get_settings()
        # Always off under test so the suite can hammer auth without throttle;
        # otherwise controlled by RATE_LIMIT_ENABLED.
        self._enabled = settings.ENV != "test" and settings.RATE_LIMIT_ENABLED

    def _key_for(self, request: Request) -> str:
        client = request.client
        ip = client.host if client else "unknown"
        return f"{ip}:{request.url.path}"

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Disabled in test env so the suite isn't throttled by its own logins;
        # toggle explicitly via RATE_LIMIT_ENABLED otherwise.
        if not self._enabled:
            return await call_next(request)
        path = request.url.path
        limit = AUTH_LIMIT if path in AUTH_PATHS else DEFAULT_LIMIT
        if not self._limiter.allow(self._key_for(request), limit):
            retry_after = limit[1]
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please slow down and try again shortly.",
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )
        return await call_next(request)
