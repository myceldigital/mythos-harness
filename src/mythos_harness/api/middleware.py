from __future__ import annotations

import hashlib
import hmac
import time
from typing import Iterable

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from mythos_harness.api.rate_limiter import (
    InMemoryRateLimiter,
    RateLimiter,
    RedisRateLimiter,
)


EXEMPT_PATH_PREFIXES = (
    "/healthz",
    "/readyz",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/app",
)
EXEMPT_PATH_EXACT = {"/"}


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool,
        api_keys: Iterable[str],
        api_key_hashes: Iterable[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.api_keys = {key for key in api_keys if key}
        self.api_key_hashes = {entry.lower() for entry in (api_key_hashes or []) if entry}

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or _is_exempt_path(request.url.path):
            return await call_next(request)
        if not self.api_keys:
            if not self.api_key_hashes:
                return JSONResponse(
                    status_code=500, content={"detail": "auth_misconfigured"}
                )

        key = _extract_api_key(request)
        if key is None or not self._is_valid_key(key):
            return JSONResponse(status_code=401, content={"detail": "unauthorized"})
        return await call_next(request)

    def _is_valid_key(self, key: str) -> bool:
        if key in self.api_keys:
            return True
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest().lower()
        for expected in self.api_key_hashes:
            if hmac.compare_digest(digest, expected):
                return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        enabled: bool,
        requests_per_window: int,
        window_seconds: int,
        key_source: str = "api_key",
        backend: str = "memory",
        redis_url: str | None = None,
        redis_prefix: str = "mythos",
        fail_open: bool = False,
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.requests_per_window = max(1, requests_per_window)
        self.window_seconds = max(1, window_seconds)
        self.key_source = key_source
        self.fail_open = fail_open
        if enabled:
            self._limiter = self._build_limiter(
                backend=backend,
                redis_url=redis_url,
                redis_prefix=redis_prefix,
            )
        else:
            self._limiter = InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled or _is_exempt_path(request.url.path):
            return await call_next(request)
        identity = self._identity_key(request)
        try:
            result = await self._limiter.check(
                identity,
                requests_per_window=self.requests_per_window,
                window_seconds=self.window_seconds,
            )
        except Exception:  # noqa: BLE001
            if self.fail_open:
                return await call_next(request)
            return JSONResponse(
                status_code=503,
                content={"detail": "rate_limiter_unavailable"},
            )
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                headers={"Retry-After": str(max(1, result.retry_after_s))},
                content={"detail": result.detail or "rate_limited"},
            )
        return await call_next(request)

    def _identity_key(self, request: Request) -> str:
        if self.key_source == "api_key":
            key = _extract_api_key(request)
            if key:
                return f"api_key:{key}"
        host = request.client.host if request.client else "unknown"
        return f"ip:{host}"

    def _build_limiter(
        self, *, backend: str, redis_url: str | None, redis_prefix: str
    ) -> RateLimiter:
        if backend == "redis":
            if not redis_url:
                raise ValueError("redis_url is required for redis rate limit backend")
            return RedisRateLimiter(redis_url=redis_url, prefix=redis_prefix)
        return InMemoryRateLimiter()


def _extract_api_key(request: Request) -> str | None:
    key = request.headers.get("x-api-key")
    if key:
        return key
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def _is_exempt_path(path: str) -> bool:
    if path in EXEMPT_PATH_EXACT:
        return True
    return any(path.startswith(prefix) for prefix in EXEMPT_PATH_PREFIXES)
