from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from mythos_harness.utils.retry import RetryConfig, retry_async


class PolicyStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    async def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"blocked_terms": [], "revision_required_terms": []}
        return json.loads(self.path.read_text(encoding="utf-8"))

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            await self.load()
            return True, "file_policy_ok"
        except Exception as exc:  # noqa: BLE001
            return False, f"file_policy_error:{exc.__class__.__name__}"


class HttpPolicyStore:
    def __init__(
        self,
        *,
        url: str,
        api_key: str | None = None,
        timeout_s: float = 20.0,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self.url = url
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.retry_config = retry_config or RetryConfig()

    async def load(self) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        async def operation() -> httpx.Response:
            async with httpx.AsyncClient(timeout=self.timeout_s) as client:
                response = await client.get(self.url, headers=headers)
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
                f"Policy DB request failed ({exc.status_code}): {exc.body}"
            ) from exc

        payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("Policy DB response must be an object.")
        return {
            "blocked_terms": list(payload.get("blocked_terms", [])),
            "revision_required_terms": list(payload.get("revision_required_terms", [])),
        }

    async def healthcheck(self) -> tuple[bool, str]:
        try:
            await self.load()
            return True, "http_policy_ok"
        except Exception as exc:  # noqa: BLE001
            return False, f"http_policy_error:{exc.__class__.__name__}"


class _HttpResponseError(Exception):
    def __init__(self, *, status_code: int, body: str):
        self.status_code = status_code
        self.body = body
        super().__init__(f"HTTP status {status_code}")


def _is_retryable_http_error(exc: Exception) -> bool:
    if isinstance(exc, _HttpResponseError):
        return exc.status_code == 429 or exc.status_code >= 500
    return isinstance(exc, (httpx.TimeoutException, httpx.TransportError))
