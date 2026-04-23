import asyncio

from mythos_harness.config import Settings
from mythos_harness.embeddings.factory import build_embedding_provider
from mythos_harness.embeddings.local import LocalDeterministicEmbeddingProvider
from mythos_harness.storage.session import _coerce_dimensions


def test_local_embedding_provider_respects_dimensions() -> None:
    settings = Settings(_env_file=None, embedding_backend="local")
    provider = build_embedding_provider(settings, dimensions=12)
    assert isinstance(provider, LocalDeterministicEmbeddingProvider)
    vector = asyncio.run(provider.embed("hello world"))
    assert len(vector) == 12


def test_coerce_dimensions_truncates_when_too_large() -> None:
    values = [1.0, 2.0, 3.0, 4.0]
    assert _coerce_dimensions(values, 2) == [1.0, 2.0]


def test_coerce_dimensions_pads_when_too_small() -> None:
    values = [1.0, 2.0]
    assert _coerce_dimensions(values, 4) == [1.0, 2.0, 0.0, 0.0]
