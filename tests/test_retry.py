import asyncio

import pytest

from mythos_harness.utils.retry import RetryConfig, retry_async


def test_retry_async_retries_then_succeeds() -> None:
    attempts = {"count": 0}

    async def operation() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = asyncio.run(
        retry_async(
            operation,
            config=RetryConfig(
                max_attempts=3,
                base_delay_s=0.0,
                max_delay_s=0.0,
                jitter_s=0.0,
            ),
            retry_if=lambda exc: isinstance(exc, RuntimeError),
        )
    )
    assert result == "ok"
    assert attempts["count"] == 3


def test_retry_async_stops_on_non_retryable() -> None:
    attempts = {"count": 0}

    async def operation() -> str:
        attempts["count"] += 1
        raise ValueError("fatal")

    with pytest.raises(ValueError):
        asyncio.run(
            retry_async(
                operation,
                config=RetryConfig(
                    max_attempts=5,
                    base_delay_s=0.0,
                    max_delay_s=0.0,
                    jitter_s=0.0,
                ),
                retry_if=lambda exc: isinstance(exc, RuntimeError),
            )
        )
    assert attempts["count"] == 1
