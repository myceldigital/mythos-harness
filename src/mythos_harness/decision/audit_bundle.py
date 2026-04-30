"""Audit bundle primitives for exporting a complete decision trail."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class AuditBundle:
    """Exportable record tying together a decision run and its artifacts."""

    run_id: str
    bundle_id: str = field(default_factory=lambda: f"aud_{uuid4().hex}")
    evidence_pack_id: str | None = None
    trajectory_id: str | None = None
    memo_id: str | None = None
    approval_ids: list[str] = field(default_factory=list)
    artifact_uris: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_artifact_uri(self, uri: str) -> None:
        self.artifact_uris.append(uri)
