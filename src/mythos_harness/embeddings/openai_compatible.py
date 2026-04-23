from __future__ import annotations

from typing import Any

import httpx

from mythos_harness.embeddings.base import EmbeddingProvider
from mythos_harness.utils.retry import RetryConfig, retry_async


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_s: float = 45.0,
        extra_headers: dict[str, str] | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_s = timeout_s
        self.extra_headers = extra_headers or {}
        self.retry_config = retry_config or RetryConfig()

    async def embed(self, text: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        payload = {"model": self.model, "input": text}

        async def operation() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers,
                )
            if response.status_code >= 400:
                raise _HttpResponseError(
                    status_code=response.status_code, body=response.text
                )
            return response

        try:
            response = await retry_async(
                operation,
                config=self.retry_config,
                retry_if=_is_retryable_http_error,
            )
        except _HttpResponseError as exc:
            raise RuntimeError(
                f"Embedding request failed ({exc.status_code}): {exc.body}"
            ) from exc
        body = response.json()
        return _extract_embedding(body)


class _HttpResponseError(Exception):
    def __init__(self, *, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP status {status_code}")


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, _HttpResponseError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


def _extract_embedding(payload: dict[str, Any]) -> list[float]:
    data = payload.get("data") or []
    if not data:
        raise RuntimeError("Embedding response missing data.")
    embedding = data[0].get("embedding")
    if not isinstance(embedding, list):
        raise RuntimeError("Embedding response has invalid embedding payload.")
    vector: list[float] = []
    for value in embedding:
        vector.append(float(value))
    return vector
