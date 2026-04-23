import pytest

from mythos_harness.config import Settings
from mythos_harness.embeddings.factory import build_embedding_provider
from mythos_harness.providers.factory import build_provider
from mythos_harness.providers.routed import RoleRoutedProvider
from mythos_harness.storage.factory import build_storage
from mythos_harness.storage.policy import PolicyStore
from mythos_harness.storage.session import SessionStore
from mythos_harness.storage.trajectory import TrajectoryStore


def test_build_provider_local_backend() -> None:
    settings = Settings(_env_file=None, provider_backend="local")
    provider = build_provider(settings)
    assert isinstance(provider, RoleRoutedProvider)


def test_build_provider_openrouter_requires_key() -> None:
    settings = Settings(
        _env_file=None,
        provider_backend="openrouter",
        provider_api_key=None,
    )
    with pytest.raises(ValueError):
        build_provider(settings)


def test_build_storage_defaults_to_local_adapters() -> None:
    settings = Settings(_env_file=None)
    storage = build_storage(settings)
    assert isinstance(storage.sessions, SessionStore)
    assert isinstance(storage.policy, PolicyStore)
    assert isinstance(storage.trajectories, TrajectoryStore)


def test_build_storage_postgres_requires_dsn() -> None:
    settings = Settings(
        _env_file=None,
        session_store_backend="postgres",
        trajectory_store_backend="postgres",
        postgres_dsn=None,
    )
    with pytest.raises(ValueError):
        build_storage(settings)


def test_build_embedding_provider_external_requires_key() -> None:
    settings = Settings(
        _env_file=None,
        embedding_backend="openai_compatible",
        embedding_api_key=None,
        provider_api_key=None,
    )
    with pytest.raises(ValueError):
        build_embedding_provider(settings, dimensions=1536)
