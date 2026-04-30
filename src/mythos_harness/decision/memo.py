"""Decision memo artifact primitives."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass(slots=True)
class DecisionMemoSection:
    """A section in an executive decision memo."""

    title: str
    body: str
    section_id: str = field(default_factory=lambda: f"sec_{uuid4().hex}")
    evidence_claim_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DecisionMemo:
    """Board-grade final artifact for a DecisionRun."""

    run_id: str
    title: str
    recommendation: str
    memo_id: str = field(default_factory=lambda: f"mem_{uuid4().hex}")
    confidence: float | None = None
    sections: list[DecisionMemoSection] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_section(self, title: str, body: str, *, evidence_claim_ids: list[str] | None = None) -> DecisionMemoSection:
        section = DecisionMemoSection(
            title=title,
            body=body,
            evidence_claim_ids=evidence_claim_ids or [],
        )
        self.sections.append(section)
        return section

    def to_markdown(self) -> str:
        confidence = "unknown" if self.confidence is None else f"{self.confidence:.2f}"
        lines = [
            f"# {self.title}",
            "",
            f"**Run ID:** `{self.run_id}`",
            f"**Confidence:** {confidence}",
            "",
            "## Recommendation",
            "",
            self.recommendation,
        ]
        for section in self.sections:
            lines.extend(["", f"## {section.title}", "", section.body])
            if section.evidence_claim_ids:
                refs = ", ".join(f"`{claim_id}`" for claim_id in section.evidence_claim_ids)
                lines.extend(["", f"Evidence claims: {refs}"])
        return "\n".join(lines).rstrip() + "\n"
