"""Human review and approval primitives for consequential runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


class ReviewStatus(str, Enum):
    """State of the human review workflow."""

    NOT_REQUESTED = "not_requested"
    REQUESTED = "requested"
    IN_REVIEW = "in_review"
    DECIDED = "decided"


class ReviewDecision(str, Enum):
    """Reviewer decision values."""

    APPROVE = "approve"
    CHALLENGE = "challenge"
    REJECT = "reject"
    REQUEST_MORE_EVIDENCE = "request_more_evidence"


@dataclass(slots=True)
class ApprovalRecord:
    """A single human review event."""

    run_id: str
    reviewer: str
    decision: ReviewDecision
    note: str | None = None
    approval_id: str = field(default_factory=lambda: f"apr_{uuid4().hex}")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_terminal(self) -> bool:
        return self.decision in {ReviewDecision.APPROVE, ReviewDecision.REJECT}
