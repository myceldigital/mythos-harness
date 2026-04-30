"""Evidence-room primitives for high-stakes decision runs.

These classes distinguish long-lived session memory from the evidence that a
specific decision run is allowed to rely on. They are intentionally lightweight
and dependency-free so they can be used by API, storage, eval, and report layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class EvidenceSourceType(StrEnum):
    """Where an evidence source came from."""

    DOCUMENT = "document"
    URL = "url"
    NOTE = "note"
    DATASET = "dataset"
    TRANSCRIPT = "transcript"
    OTHER = "other"


class EvidenceReliability(StrEnum):
    """Coarse reliability score used before domain-specific scoring exists."""

    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceAdmissibility(StrEnum):
    """Whether a source may be used in a decision memo."""

    PENDING = "pending"
    ADMISSIBLE = "admissible"
    LIMITED = "limited"
    EXCLUDED = "excluded"


@dataclass(slots=True)
class EvidenceClaim:
    """A claim extracted from a source.

    A claim is deliberately smaller than a document. Branches and judges should
    argue over claims with citations, not vague references to uploaded files.
    """

    text: str
    source_id: str
    claim_id: str = field(default_factory=lambda: f"claim_{uuid4().hex}")
    confidence: float | None = None
    quote: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceSource:
    """A source admitted into a run-specific evidence room."""

    title: str
    source_type: EvidenceSourceType = EvidenceSourceType.DOCUMENT
    source_id: str = field(default_factory=lambda: f"src_{uuid4().hex}")
    uri: str | None = None
    owner: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reliability: EvidenceReliability = EvidenceReliability.UNKNOWN
    admissibility: EvidenceAdmissibility = EvidenceAdmissibility.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    claims: list[EvidenceClaim] = field(default_factory=list)

    def add_claim(self, text: str, *, confidence: float | None = None, quote: str | None = None) -> EvidenceClaim:
        claim = EvidenceClaim(text=text, source_id=self.source_id, confidence=confidence, quote=quote)
        self.claims.append(claim)
        return claim


@dataclass(slots=True)
class EvidencePack:
    """Evidence admitted for a single decision run.

    Session memory can suggest context. Evidence packs define what the run may
    cite, challenge, and export.
    """

    name: str
    pack_id: str = field(default_factory=lambda: f"evp_{uuid4().hex}")
    description: str | None = None
    sources: list[EvidenceSource] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_source(self, source: EvidenceSource) -> EvidenceSource:
        self.sources.append(source)
        return source

    @property
    def claims(self) -> list[EvidenceClaim]:
        return [claim for source in self.sources for claim in source.claims]

    def admissible_sources(self) -> list[EvidenceSource]:
        return [
            source
            for source in self.sources
            if source.admissibility in {EvidenceAdmissibility.ADMISSIBLE, EvidenceAdmissibility.LIMITED}
        ]
