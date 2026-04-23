from __future__ import annotations

from typing import Any, Protocol

from mythos_harness.core.state import StructuredState


class SessionStoreContract(Protocol):
    async def get(self, thread_id: str) -> StructuredState | None:
        ...

    async def put(self, thread_id: str, state: StructuredState) -> None:
        ...

    async def search_similar(
        self,
        query: str,
        *,
        limit: int = 3,
        exclude_thread_id: str | None = None,
    ) -> list[StructuredState]:
        ...

    async def healthcheck(self) -> tuple[bool, str]:
        ...


class PolicyStoreContract(Protocol):
    async def load(self) -> dict[str, Any]:
        ...

    async def healthcheck(self) -> tuple[bool, str]:
        ...


class TrajectoryStoreContract(Protocol):
    async def write(self, payload: dict[str, Any]) -> None:
        ...

    async def healthcheck(self) -> tuple[bool, str]:
        ...
