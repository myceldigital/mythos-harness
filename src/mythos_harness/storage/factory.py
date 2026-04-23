from __future__ import annotations

from dataclasses import dataclass

from mythos_harness.config import Settings
from mythos_harness.embeddings.factory import build_embedding_provider
from mythos_harness.storage.contracts import (
    PolicyStoreContract,
    SessionStoreContract,
    TrajectoryStoreContract,
)
from mythos_harness.storage.policy import HttpPolicyStore, PolicyStore
from mythos_harness.storage.session import PostgresSessionStore, SessionStore
from mythos_harness.storage.trajectory import (
    HttpTrajectoryStore,
    PostgresTrajectoryStore,
    TrajectoryStore,
)
from mythos_harness.utils.retry import RetryConfig


@dataclass(slots=True)
class StorageBundle:
    sessions: SessionStoreContract
    policy: PolicyStoreContract
    trajectories: TrajectoryStoreContract


def build_storage(settings: Settings) -> StorageBundle:
    retry_config = RetryConfig(
        max_attempts=settings.retry_max_attempts,
        base_delay_s=settings.retry_base_delay_s,
        max_delay_s=settings.retry_max_delay_s,
        jitter_s=settings.retry_jitter_s,
    )
    sessions = _build_session_store(settings)
    policy = _build_policy_store(settings, retry_config=retry_config)
    trajectories = _build_trajectory_store(settings, retry_config=retry_config)
    return StorageBundle(sessions=sessions, policy=policy, trajectories=trajectories)


def _build_session_store(settings: Settings) -> SessionStoreContract:
    if settings.session_store_backend == "memory":
        return SessionStore()
    if settings.session_store_backend == "postgres":
        if not settings.postgres_dsn:
            raise ValueError("MYTHOS_POSTGRES_DSN is required for postgres session store.")
        embedding_provider = build_embedding_provider(
            settings,
            dimensions=settings.pgvector_dimensions,
        )
        return PostgresSessionStore(
            dsn=settings.postgres_dsn,
            schema=settings.postgres_schema,
            vector_dimensions=settings.pgvector_dimensions,
            embedding_provider=embedding_provider,
            retry_config=RetryConfig(
                max_attempts=settings.retry_max_attempts,
                base_delay_s=settings.retry_base_delay_s,
                max_delay_s=settings.retry_max_delay_s,
                jitter_s=settings.retry_jitter_s,
            ),
        )
    raise ValueError(f"Unsupported session store backend: {settings.session_store_backend}")


def _build_policy_store(
    settings: Settings, *, retry_config: RetryConfig
) -> PolicyStoreContract:
    if settings.policy_store_backend == "file":
        return PolicyStore(settings.policy_path)
    if settings.policy_store_backend == "http":
        if not settings.policy_http_url:
            raise ValueError("MYTHOS_POLICY_HTTP_URL is required for HTTP policy store.")
        return HttpPolicyStore(
            url=settings.policy_http_url,
            api_key=settings.policy_http_api_key,
            retry_config=retry_config,
        )
    raise ValueError(f"Unsupported policy store backend: {settings.policy_store_backend}")


def _build_trajectory_store(
    settings: Settings, *, retry_config: RetryConfig
) -> TrajectoryStoreContract:
    if settings.trajectory_store_backend == "jsonl":
        return TrajectoryStore(settings.trajectory_store_path)
    if settings.trajectory_store_backend == "postgres":
        if not settings.postgres_dsn:
            raise ValueError(
                "MYTHOS_POSTGRES_DSN is required for postgres trajectory store."
            )
        return PostgresTrajectoryStore(
            dsn=settings.postgres_dsn,
            schema=settings.postgres_schema,
            retry_config=retry_config,
        )
    if settings.trajectory_store_backend == "http":
        if not settings.trajectory_http_url:
            raise ValueError(
                "MYTHOS_TRAJECTORY_HTTP_URL is required for HTTP trajectory store."
            )
        return HttpTrajectoryStore(
            url=settings.trajectory_http_url,
            api_key=settings.trajectory_http_api_key,
            retry_config=retry_config,
        )
    raise ValueError(
        f"Unsupported trajectory store backend: {settings.trajectory_store_backend}"
    )
