from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from mythos_harness.api.middleware import ApiKeyAuthMiddleware, RateLimitMiddleware
from mythos_harness.api.observability import (
    AccessLogMiddleware,
    MetricsMiddleware,
    RequestIdMiddleware,
    add_metrics_route,
)
from mythos_harness.api import router as mythos_router
from mythos_harness.config import Settings, get_settings
from mythos_harness.core.service import MythosOrchestrator
from mythos_harness.providers.factory import build_provider
from mythos_harness.storage.factory import build_storage
from mythos_harness.utils.logging import configure_logging


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    provider = build_provider(settings)
    stores = build_storage(settings)
    orchestrator = MythosOrchestrator(
        settings=settings,
        provider=provider,
        session_store=stores.sessions,
        policy_store=stores.policy,
        trajectory_store=stores.trajectories,
    )

    app = FastAPI(
        title="Mythos Harness",
        description="Mythos Harness v0.3 orchestration runtime.",
        version="0.3.0",
    )
    web_root = Path(__file__).resolve().parent / "web"
    static_root = web_root / "static"
    if static_root.exists():
        app.mount("/app/static", StaticFiles(directory=static_root), name="app-static")
    auth_keys = [token.strip() for token in settings.api_auth_keys.split(",")]
    auth_key_hashes = [token.strip() for token in settings.api_auth_key_hashes.split(",")]
    app.add_middleware(
        RequestIdMiddleware,
        header_name=settings.request_id_header,
    )
    app.add_middleware(
        AccessLogMiddleware,
        enabled=settings.access_log_enabled,
    )
    app.add_middleware(
        MetricsMiddleware,
        enabled=settings.metrics_enabled,
    )
    app.add_middleware(
        ApiKeyAuthMiddleware,
        enabled=settings.api_auth_enabled,
        api_keys=auth_keys,
        api_key_hashes=auth_key_hashes,
    )
    app.add_middleware(
        RateLimitMiddleware,
        enabled=settings.rate_limit_enabled,
        requests_per_window=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_s,
        key_source=settings.rate_limit_key_source,
        backend=settings.rate_limit_backend,
        redis_url=settings.redis_url,
        redis_prefix=settings.redis_prefix,
        fail_open=settings.rate_limit_fail_open,
    )

    async def orchestrator_dependency() -> MythosOrchestrator:
        return orchestrator

    app.dependency_overrides[mythos_router.get_orchestrator] = orchestrator_dependency
    app.include_router(mythos_router.router)

    @app.get("/", include_in_schema=False)
    async def ui_root() -> RedirectResponse:
        return RedirectResponse(url="/app", status_code=307)

    @app.get("/app", include_in_schema=False)
    async def ui_app() -> FileResponse:
        return FileResponse(web_root / "index.html")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    async def readyz() -> JSONResponse:
        result = await orchestrator.readiness()
        status_code = 200 if result.get("ok") else 503
        return JSONResponse(status_code=status_code, content=result)

    add_metrics_route(app, enabled=settings.metrics_enabled)

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run("mythos_harness.main:app", host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
