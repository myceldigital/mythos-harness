"""Evaluation scoring primitives.

These are intentionally simple and model-agnostic. The near-term goal is to make
baseline direct calls comparable with Mythos-wrapped runs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class ScoreDimension(str, Enum):
    """Dimensions used to test decision-quality uplift."""

    FACTUALITY = "factuality"
    REASONING_QUALITY = "reasoning_quality"
    CALIBRATION = "calibration"
    ASSUMPTION_DISCOVERY = "assumption_discovery"
    COUNTERARGUMENT_QUALITY = "counterargument_quality"
    MISSING_EVIDENCE_DETECTION = "missing_evidence_detection"
    DECISION_USEFULNESS = "decision_usefulness"
    COST_EFFICIENCY = "cost_efficiency"


@dataclass(slots=True)
class EvalScore:
    """A score assigned to an answer or decision memo."""

    dimension: ScoreDimension
    score: float
    rationale: str
    score_id: str = field(default_factory=lambda: f"scr_{uuid4().hex}")
    judge: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def normalized(self) -> float:
        return max(0.0, min(1.0, self.score))
