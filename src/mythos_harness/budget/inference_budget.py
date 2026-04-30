"""Inference budget model.

Mythos should spend tokens like capital. These primitives let future orchestrator
code decide whether another branch, judge pass, or repair loop is worth the
marginal cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4


class EscalationPolicy(str, Enum):
    """How aggressively a run may spend additional inference."""

    NEVER = "never"
    ON_LOW_CONFIDENCE = "on_low_confidence"
    ON_CONTRADICTION = "on_contradiction"
    ON_HIGH_STAKES = "on_high_stakes"
    ALWAYS = "always"


@dataclass(slots=True)
class SpendDecision:
    """Decision returned by a budget check."""

    allowed: bool
    reason: str
    remaining_tokens: int | None = None
    remaining_cost_usd: float | None = None


@dataclass(slots=True)
class InferenceBudget:
    """Token, cost, latency, and depth envelope for a run."""

    max_tokens: int | None = None
    max_cost_usd: float | None = None
    max_latency_s: float | None = None
    reasoning_depth: str = "deep"
    escalation_policy: EscalationPolicy = EscalationPolicy.ON_LOW_CONFIDENCE
    budget_id: str = field(default_factory=lambda: f"bud_{uuid4().hex}")
    spent_tokens: int = 0
    spent_cost_usd: float = 0.0
    elapsed_s: float = 0.0

    def record_spend(self, *, tokens: int = 0, cost_usd: float = 0.0, elapsed_s: float = 0.0) -> None:
        self.spent_tokens += max(tokens, 0)
        self.spent_cost_usd += max(cost_usd, 0.0)
        self.elapsed_s += max(elapsed_s, 0.0)

    def can_spend(
        self,
        *,
        estimated_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        estimated_latency_s: float = 0.0,
    ) -> SpendDecision:
        if self.max_tokens is not None and self.spent_tokens + estimated_tokens > self.max_tokens:
            return SpendDecision(False, "token budget exceeded", self.max_tokens - self.spent_tokens, None)
        if self.max_cost_usd is not None and self.spent_cost_usd + estimated_cost_usd > self.max_cost_usd:
            return SpendDecision(False, "cost budget exceeded", None, self.max_cost_usd - self.spent_cost_usd)
        if self.max_latency_s is not None and self.elapsed_s + estimated_latency_s > self.max_latency_s:
            return SpendDecision(False, "latency budget exceeded")
        remaining_tokens = None if self.max_tokens is None else self.max_tokens - self.spent_tokens - estimated_tokens
        remaining_cost = None if self.max_cost_usd is None else self.max_cost_usd - self.spent_cost_usd - estimated_cost_usd
        return SpendDecision(True, "within budget", remaining_tokens, remaining_cost)
