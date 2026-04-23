from __future__ import annotations

import hashlib

from mythos_harness.embeddings.base import EmbeddingProvider


class LocalDeterministicEmbeddingProvider(EmbeddingProvider):
    """Deterministic fallback embedding provider for local/offline runs."""

    def __init__(self, dimensions: int) -> None:
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for idx in range(self.dimensions):
            byte = digest[idx % len(digest)]
            values.append(round(byte / 255.0, 6))
        return values
