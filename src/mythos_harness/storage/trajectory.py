from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import asyncpg
import httpx

from mythos_harness.utils.retry import RetryConfig, retry_async


class TrajectoryStore:
    """Append-only JSONL trajectory log storage."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    async def write(self, payload: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=True) + "\n")

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8"):
                pass
            return True, "jsonl_ok"
        except Exception as exc:  # noqa: BLE001
            return False, f"jsonl_error:{exc.__class__.__name__}"


class PostgresTrajectoryStore:
    """Trajectory logs persisted in Postgres (warehouse-friendly JSONB)."""

    def __init__(
        self, dsn: str, schema: str, retry_config: RetryConfig | None = None
    ) -> None:
        self.dsn = dsn
        self.schema = schema
        self.retry_config = retry_config or RetryConfig()
        self._pool: asyncpg.Pool | None = None

    async def write(self, payload: dict[str, Any]) -> None:
        trajectory_id = str(payload.get("id", "unknown"))

        async def operation() -> None:
            pool = await self._pool_or_init()
            async with pool.acquire() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self.schema}.trajectory_logs (id, payload)
                    VALUES ($1, $2::jsonb)
                    ON CONFLICT (id)
                    DO UPDATE SET payload = EXCLUDED.payload, created_at = now()
                    """,
                    trajectory_id,
                    json.dumps(payload),
                )

        await retry_async(
            operation,
            config=self.retry_config,
            retry_if=_is_retryable_postgres_error,
        )

    async def _pool_or_init(self) -> asyncpg.Pool:
        if self._pool is not None:
            return self._pool

        async def operation() -> asyncpg.Pool:
            pool = await asyncpg.create_pool(self.dsn)
            async with pool.acquire() as conn:
                await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
                await conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.schema}.trajectory_logs (
                        id TEXT PRIMARY KEY,
                        payload JSONB NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            return pool

        self._pool = await retry_async(
            operation,
            config=self.retry_config,
            retry_if=_is_retryable_postgres_error,
        )
        return self._pool

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            pool = await self._pool_or_init()
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
            return True, "postgres_ok"
        except Exception as exc:  # noqa: BLE001
            return False, f"postgres_error:{exc.__class__.__name__}"


class HttpTrajectoryStore:
    """Push trajectories to external warehouse ingestion endpoint."""

    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        timeout_s: float = 20.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.retry_config = retry_config or RetryConfig()

    async def write(self, payload: dict[str, Any]) -> None:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async def operation() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(self.url, json=payload, headers=headers)
            if response.status_code >= 400:
                raise _HttpResponseError(
                    status_code=response.status_code, body=response.text
                )
            return response

        try:
            await retry_async(
                operation,
                config=self.retry_config,
                retry_if=_is_retryable_http_error,
            )
        except _HttpResponseError as exc:
            raise RuntimeError(
                f"Trajectory warehouse request failed ({exc.status_code}): {exc.body}"
            ) from exc

    async def healthcheck(self) -> tuple[bool, str]:
        if not self.url:
            return False, "http_sink_missing_url"
        return True, "http_sink_configured"


class _HttpResponseError(Exception):
    def __init__(self, *, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP status {status_code}")


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, _HttpResponseError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


def _is_retryable_postgres_error(exc: Exception) -> bool:
    retryable = (
        asyncpg.PostgresConnectionError,
        asyncpg.ConnectionDoesNotExistError,
        asyncpg.CannotConnectNowError,
        asyncpg.TooManyConnectionsError,
        asyncpg.SerializationError,
        asyncpg.DeadlockDetectedError,
        asyncpg.InterfaceError,
    )
    return isinstance(exc, retryable)
