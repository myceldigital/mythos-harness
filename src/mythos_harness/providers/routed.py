from __future__ import annotations

from typing import AsyncIterator

from mythos_harness.providers.base import ModelProvider


class RoleRoutedProvider(ModelProvider):
    """Routes judge traffic to alternate provider when configured."""

    def __init__(
        self,
        *,
        primary: ModelProvider,
        judge_model: str,
        judge_provider: ModelProvider | None = None,
    ) -> None:
        self.primary = primary
        self.judge_model = judge_model
        self.judge_provider = judge_provider

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, str]:
        provider = self.primary
        if self.judge_provider is not None and model == self.judge_model:
            provider = self.judge_provider
        return await provider.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def stream_complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        provider = self.primary
        if self.judge_provider is not None and model == self.judge_model:
            provider = self.judge_provider
        async for token in provider.stream_complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        ):
            yield token
