from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass

import asyncpg

from mythos_harness.core.state import StructuredState
from mythos_harness.embeddings.base import EmbeddingProvider
from mythos_harness.utils.retry import RetryConfig, retry_async


class SessionStore:
    """In-memory session snapshots."""

    def __init__(self) -> None:
        self._snapshots: dict[str, StructuredState] = {}

    async def get(self, thread_id: str) -> StructuredState | None:
        state = self._snapshots.get(thread_id)
        return deepcopy(state) if state else None

    async def put(self, thread_id: str, state: StructuredState) -> None:
        self._snapshots[thread_id] = deepcopy(state)

    async def search_similar(
        self,
        query: str,
        *,
        limit: int = 3,
        exclude_thread_id: str | None = None,
    ) -> list[StructuredState]:
        query_terms = set(query.lower().split())
        ranked: list[_RankedState] = []
        for thread_id, state in self._snapshots.items():
            if exclude_thread_id and thread_id == exclude_thread_id:
                continue
            text = _state_text(state)
            if not text:
                continue
            score = len(query_terms.intersection(set(text.lower().split())))
            if score > 0:
                ranked.append(_RankedState(score=score, state=state))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return [deepcopy(item.state) for item in ranked[: max(1, limit)]]

    async def healthcheck(self) -> tuple[bool, str]:
        return True, "memory_ok"


class PostgresSessionStore:
    """Session snapshots persisted in Postgres with pgvector embedding column."""

    def __init__(
        self,
        dsn: str,
        schema: str,
        *,
        vector_dimensions: int = 1536,
        embedding_provider: EmbeddingProvider,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.dsn = dsn
        self.schema = schema
        self.vector_dimensions = vector_dimensions
        self.embedding_provider = embedding_provider
        self.retry_config = retry_config or RetryConfig()
        self._pool: asyncpg.Pool | None = None

    async def get(self, thread_id: str) -> StructuredState | None:
        async def operation() -> StructuredState | None:
            pool = await self._pool_or_init()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    f"SELECT snapshot_json FROM {self.schema}.session_snapshots WHERE thread_id=$1",
                    thread_id,
                )
            if row is None:
                return None
            payload = row["snapshot_json"]
            if isinstance(payload, str):
                payload = json.loads(payload)
            return StructuredState.from_dict(payload)

        return await retry_async(
            operation,
            config=self.retry_config,
            retry_if=_is_retryable_postgres_error,
        )

    async def put(self, thread_id: str, state: StructuredState) -> None:
        payload = state.as_dict()
        embedding_literal = await _embedding_vector_literal(
            payload,
            dimensions=self.vector_dimensions,
            embedding_provider=self.embedding_provider,
        )

        async def operation() -> None:
            pool = await self._pool_or_init()
            async with pool.acquire() as conn:
                await conn.execute(
                    f"""
                    INSERT INTO {self.schema}.session_snapshots (thread_id, snapshot_json, embedding)
                    VALUES ($1, $2::jsonb, $3::vector)
                    ON CONFLICT (thread_id)
                    DO UPDATE SET
                        snapshot_json = EXCLUDED.snapshot_json,
                        embedding = EXCLUDED.embedding,
                        updated_at = now()
                    """,
                    thread_id,
                    json.dumps(payload),
                    embedding_literal,
                )

        await retry_async(
            operation,
            config=self.retry_config,
            retry_if=_is_retryable_postgres_error,
        )

    async def search_similar(
        self,
        query: str,
        *,
        limit: int = 3,
        exclude_thread_id: str | None = None,
    ) -> list[StructuredState]:
        embedding = await self.embedding_provider.embed(query)
        embedding_literal = "[" + ",".join(str(v) for v in _coerce_dimensions(embedding, self.vector_dimensions)) + "]"

        async def operation() -> list[StructuredState]:
            pool = await self._pool_or_init()
            async with pool.acquire() as conn:
                if exclude_thread_id:
                    rows = await conn.fetch(
                        f"""
                        SELECT snapshot_json
                        FROM {self.schema}.session_snapshots
                        WHERE embedding IS NOT NULL AND thread_id <> $2
                        ORDER BY embedding <-> $1::vector
                        LIMIT $3
                        """,
                        embedding_literal,
                        exclude_thread_id,
                        max(1, limit),
                    )
                else:
                    rows = await conn.fetch(
                        f"""
                        SELECT snapshot_json
                        FROM {self.schema}.session_snapshots
                        WHERE embedding IS NOT NULL
                        ORDER BY embedding <-> $1::vector
                        LIMIT $2
                        """,
                        embedding_literal,
                        max(1, limit),
                    )
            results: list[StructuredState] = []
            for row in rows:
                payload = row["snapshot_json"]
                if isinstance(payload, str):
                    payload = json.loads(payload)
                results.append(StructuredState.from_dict(payload))
            return results

        return await retry_async(
            operation,
            config=self.retry_config,
            retry_if=_is_retryable_postgres_error,
        )

    async def _pool_or_init(self) -> asyncpg.Pool:
        if self._pool is not None:
            return self._pool

        async def operation() -> asyncpg.Pool:
            pool = await asyncpg.create_pool(self.dsn)
            await _ensure_session_schema(pool, self.schema, self.vector_dimensions)
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


@dataclass(slots=True)
class _RankedState:
    score: int
    state: StructuredState


def _state_text(state: StructuredState) -> str:
    top = state.top_hypothesis()
    if top is not None:
        return top.answer
    if state.facts:
        return " ".join(f.claim for f in state.facts[:4])
    return ""


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


async def _ensure_session_schema(
    pool: asyncpg.Pool, schema: str, vector_dimensions: int
) -> None:
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {schema}.session_snapshots (
                thread_id TEXT PRIMARY KEY,
                snapshot_json JSONB NOT NULL,
                embedding VECTOR({vector_dimensions}),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


async def _embedding_vector_literal(
    payload: dict[str, object],
    *,
    dimensions: int,
    embedding_provider: EmbeddingProvider,
) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=True)
    values = await embedding_provider.embed(raw)
    coerced = _coerce_dimensions(values, dimensions)
    return "[" + ",".join(str(round(v, 8)) for v in coerced) + "]"


def _coerce_dimensions(values: list[float], dimensions: int) -> list[float]:
    if len(values) == dimensions:
        return values
    if len(values) > dimensions:
        return values[:dimensions]
    if not values:
        return [0.0] * dimensions
    padded = list(values)
    padded.extend([0.0] * (dimensions - len(values)))
    return padded
