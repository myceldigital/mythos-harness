from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.providers.base import ModelProvider
from mythos_harness.providers.local import LocalDeterministicProvider
from mythos_harness.providers.openai_compatible import OpenAICompatibleProvider
from mythos_harness.providers.routed import RoleRoutedProvider
from mythos_harness.utils.retry import RetryConfig


def build_provider(settings: Settings) -> ModelProvider:
    retry_config = RetryConfig(
        max_attempts=settings.retry_max_attempts,
        base_delay_s=settings.retry_base_delay_s,
        max_delay_s=settings.retry_max_delay_s,
        jitter_s=settings.retry_jitter_s,
    )
    primary = _build_single_provider(
        backend=settings.provider_backend,
        api_key=settings.provider_api_key,
        base_url=settings.provider_base_url,
        timeout_s=settings.provider_timeout_s,
        openrouter_site_url=settings.openrouter_site_url,
        openrouter_app_name=settings.openrouter_app_name,
        retry_config=retry_config,
    )

    judge_provider = None
    if settings.judge_provider_backend:
        judge_provider = _build_single_provider(
            backend=settings.judge_provider_backend,
            api_key=settings.judge_provider_api_key or settings.provider_api_key,
            base_url=settings.judge_provider_base_url or settings.provider_base_url,
            timeout_s=settings.provider_timeout_s,
            openrouter_site_url=settings.openrouter_site_url,
            openrouter_app_name=settings.openrouter_app_name,
            retry_config=retry_config,
        )

    return RoleRoutedProvider(
        primary=primary,
        judge_model=settings.model_judge,
        judge_provider=judge_provider,
    )


def _build_single_provider(
    *,
    backend: str,
    api_key: str | None,
    base_url: str,
    timeout_s: float,
    openrouter_site_url: str | None,
    openrouter_app_name: str,
    retry_config: RetryConfig,
) -> ModelProvider:
    if backend == "local":
        return LocalDeterministicProvider()

    if backend == "openai_compatible":
        if not api_key:
            raise ValueError(
                "MYTHOS_PROVIDER_API_KEY (or judge equivalent) is required for openai_compatible backend."
            )
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url=base_url,
            timeout_s=timeout_s,
            retry_config=retry_config,
        )

    if backend == "openrouter":
        if not api_key:
            raise ValueError(
                "MYTHOS_PROVIDER_API_KEY (or judge equivalent) is required for openrouter backend."
            )
        headers: dict[str, str] = {
            "HTTP-Referer": openrouter_site_url or "https://github.com/myceldigital/mythos-harness",
            "X-Title": openrouter_app_name,
        }
        return OpenAICompatibleProvider(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            timeout_s=timeout_s,
            extra_headers=headers,
            retry_config=retry_config,
        )

    raise ValueError(f"Unsupported provider backend: {backend}")
