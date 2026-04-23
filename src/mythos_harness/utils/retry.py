from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")


@dataclass(slots=True)
class RetryConfig:
    max_attempts: int = 3
    base_delay_s: float = 0.25
    max_delay_s: float = 2.0
    jitter_s: float = 0.05


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    config: RetryConfig,
    retry_if: Callable[[Exception], bool],
) -> T:
    attempts = max(1, config.max_attempts)
    for attempt in range(1, attempts + 1):
        try:
            return await operation()
        except Exception as exc:  # noqa: BLE001
            should_retry = retry_if(exc) and attempt < attempts
            if not should_retry:
                raise
            delay = min(config.max_delay_s, config.base_delay_s * (2 ** (attempt - 1)))
            jitter = random.uniform(0, config.jitter_s) if config.jitter_s > 0 else 0.0
            await asyncio.sleep(delay + jitter)
    raise RuntimeError("Retry loop exhausted unexpectedly.")
