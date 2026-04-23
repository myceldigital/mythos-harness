from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.embeddings.base import EmbeddingProvider
from mythos_harness.embeddings.local import LocalDeterministicEmbeddingProvider
from mythos_harness.embeddings.openai_compatible import (
    OpenAICompatibleEmbeddingProvider,
)
from mythos_harness.utils.retry import RetryConfig


def build_embedding_provider(
    settings: Settings,
    *,
    dimensions: int,
) -> EmbeddingProvider:
    backend = settings.embedding_backend
    retry_config = RetryConfig(
        max_attempts=settings.retry_max_attempts,
        base_delay_s=settings.retry_base_delay_s,
        max_delay_s=settings.retry_max_delay_s,
        jitter_s=settings.retry_jitter_s,
    )
    if backend == "local":
        return LocalDeterministicEmbeddingProvider(dimensions=dimensions)

    api_key = settings.embedding_api_key or settings.provider_api_key
    if not api_key:
        raise ValueError(
            "MYTHOS_EMBEDDING_API_KEY (or MYTHOS_PROVIDER_API_KEY fallback) is required for external embedding backends."
        )

    base_url = settings.embedding_base_url or settings.provider_base_url
    if backend == "openai_compatible":
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url=base_url,
            model=settings.embedding_model,
            timeout_s=settings.embedding_timeout_s,
            retry_config=retry_config,
        )

    if backend == "openrouter":
        headers = {
            "HTTP-Referer": settings.openrouter_site_url
            or "https://github.com/myceldigital/mythos-harness",
            "X-Title": settings.openrouter_app_name,
        }
        return OpenAICompatibleEmbeddingProvider(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model=settings.embedding_model,
            timeout_s=settings.embedding_timeout_s,
            extra_headers=headers,
            retry_config=retry_config,
        )

    raise ValueError(f"Unsupported embedding backend: {backend}")
