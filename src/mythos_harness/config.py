from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MYTHOS_")

    env: str = "development"
    host: str = "0.0.0.0"
    port: int = 8080
    max_loops: int = 6

    model_base: str = "base-reasoning"
    model_fast: str = "fast-triage"
    model_judge: str = "external-judge"
    model_code_math: str = "code-math"
    model_style: str = "style-harmonizer"

    provider_backend: Literal["local", "openai_compatible", "openrouter"] = "local"
    provider_api_key: str | None = None
    provider_base_url: str = "https://api.openai.com/v1"
    provider_timeout_s: float = 60.0
    openrouter_site_url: str | None = None
    openrouter_app_name: str = "mythos-harness"

    judge_provider_backend: Literal["", "local", "openai_compatible", "openrouter"] = ""
    judge_provider_api_key: str | None = None
    judge_provider_base_url: str | None = None

    session_store_backend: Literal["memory", "postgres"] = "memory"
    trajectory_store_backend: Literal["jsonl", "postgres", "http"] = "jsonl"
    policy_store_backend: Literal["file", "http"] = "file"

    postgres_dsn: str | None = None
    postgres_schema: str = "mythos"
    pgvector_dimensions: int = 1536

    embedding_backend: Literal["local", "openai_compatible", "openrouter"] = "local"
    embedding_model: str = "text-embedding-3-small"
    embedding_api_key: str | None = None
    embedding_base_url: str | None = None
    embedding_timeout_s: float = 45.0

    trajectory_http_url: str | None = None
    trajectory_http_api_key: str | None = None
    policy_http_url: str | None = None
    policy_http_api_key: str | None = None

    api_auth_enabled: bool = False
    api_auth_keys: str = ""
    api_auth_key_hashes: str = ""
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 60
    rate_limit_window_s: int = 60
    rate_limit_key_source: Literal["api_key", "ip"] = "api_key"
    rate_limit_backend: Literal["memory", "redis"] = "memory"
    rate_limit_fail_open: bool = False

    redis_url: str | None = None
    redis_prefix: str = "mythos"

    metrics_enabled: bool = True
    access_log_enabled: bool = True
    request_id_header: str = "x-request-id"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    retry_max_attempts: int = 3
    retry_base_delay_s: float = 0.25
    retry_max_delay_s: float = 2.0
    retry_jitter_s: float = 0.05

    memory_retrieval_k: int = 3

    trajectory_store_path: Path = Path("data/trajectories.jsonl")
    policy_path: Path = Path("config/policy_rules.json")

    default_confidence_threshold: float = 0.72
    max_branches: int = 3


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
