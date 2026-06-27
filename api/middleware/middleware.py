"""Rate limiting, correlation ID, and graceful shutdown middleware."""

import time
import uuid
import signal
import sqlite3
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


# ── Rate Limiter ──────────────────────────────────────

class RateLimiter:
    """Sliding window rate limiter per IP."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)

    def check(self, ip: str) -> tuple[bool, int]:
        now = time.time()
        cutoff = now - self.window
        timestamps = self._clients[ip]
        timestamps[:] = [t for t in timestamps if t > cutoff]
        timestamps.append(now)
        remaining = max(0, self.max_requests - len(timestamps))
        return len(timestamps) <= self.max_requests, remaining


# ── Middleware ────────────────────────────────────────

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, rate_limiter: RateLimiter | None = None):
        super().__init__(app)
        self.limiter = rate_limiter or RateLimiter()

    async def dispatch(self, request: Request, call_next):
        ip = request.client.host if request.client else "unknown"
        allowed, remaining = self.limiter.check(ip)
        if not allowed:
            from fastapi.responses import JSONResponse
            resp = JSONResponse(
                {"detail": "Rate limit exceeded. Try again later."},
                status_code=429,
            )
            resp.headers["X-RateLimit-Remaining"] = "0"
            return resp
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Inject X-Request-ID header into every response."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


# ── Request Body Size Limit ──────────────────────────

class MaxBodySizeMiddleware(BaseHTTPMiddleware):
    """Reject requests with body larger than max_body_size bytes."""

    def __init__(self, app: ASGIApp, max_body_size: int = 1_048_576):
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                {"detail": f"Request body too large. Max {self.max_body_size // 1024} KB."},
                status_code=413,
            )
        return await call_next(request)


# ── Global Error Handler ──────────────────────────────

from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


async def global_validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": exc.errors()},
    )


async def global_http_error_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


async def global_unhandled_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Graceful Shutdown ─────────────────────────────────

_shutdown_hooks: list[callable] = []


def register_shutdown_hook(fn: callable):
    _shutdown_hooks.append(fn)


def _handle_shutdown(signum, frame):
    print(f"\n[Shutdown] Signal {signum} received. Cleaning up...")
    for fn in _shutdown_hooks:
        try:
            fn()
        except Exception as e:
            print(f"[Shutdown] Hook error: {e}")
    print("[Shutdown] Done.")
    exit(0)


def setup_signal_handlers():
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
