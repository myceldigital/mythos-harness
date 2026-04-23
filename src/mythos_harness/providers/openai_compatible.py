from __future__ import annotations

from typing import Any

import httpx

from mythos_harness.providers.base import ModelProvider
from mythos_harness.utils.retry import RetryConfig, retry_async


class OpenAICompatibleProvider(ModelProvider):
    """OpenAI-compatible chat completion adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_s: float = 60.0,
        extra_headers: dict[str, str] | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.extra_headers = extra_headers or {}
        self.retry_config = retry_config or RetryConfig()

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, str]:
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }

        async def operation() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
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
                f"Provider request failed ({exc.status_code}): {exc.body}"
            ) from exc

        body = response.json()
        return {"content": _extract_content(body)}


class _HttpResponseError(Exception):
    def __init__(self, *, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP status {status_code}")


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, _HttpResponseError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))


def _extract_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks).strip()
    return str(content or "")
