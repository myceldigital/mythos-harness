"""DecisionRun domain model.

DecisionRun is the first-class object for the Mythos high-stakes harness thesis.
Chat and completion endpoints can remain as interfaces, but consequential work
should be represented as durable runs with evidence, branches, budgets, review
status, and exportable artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from mythos_harness.decision.evidence_pack import EvidencePack


class RunStatus(str, Enum):
    """Lifecycle state for a decision run."""

    DRAFT = "draft"
    TRIAGED = "triaged"
    RUNNING = "running"
    WAITING_FOR_REVIEW = "waiting_for_review"
    APPROVED = "approved"
    CHALLENGED = "challenged"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class Assumption:
    """An explicit assumption that may support or break a recommendation."""

    text: str
    assumption_id: str = field(default_factory=lambda: f"asm_{uuid4().hex}")
    importance: str = "medium"
    evidence_claim_ids: list[str] = field(default_factory=list)
    would_change_conclusion: bool = False


@dataclass(slots=True)
class Contradiction:
    """A conflict detected between claims, assumptions, or branches."""

    description: str
    contradiction_id: str = field(default_factory=lambda: f"ctr_{uuid4().hex}")
    related_ids: list[str] = field(default_factory=list)
    severity: str = "medium"
    resolved: bool = False
    resolution_note: str | None = None


@dataclass(slots=True)
class DecisionBranch:
    """A named adversarial or constructive branch in a decision run."""

    role: str
    thesis: str
    branch_id: str = field(default_factory=lambda: f"br_{uuid4().hex}")
    arguments: list[str] = field(default_factory=list)
    evidence_claim_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    status: str = "open"


@dataclass(slots=True)
class DecisionRun:
    """Durable high-stakes reasoning unit."""

    question: str
    domain: str = "general"
    risk_level: str = "unknown"
    execution_mode: str = "deep"
    run_id: str = field(default_factory=lambda: f"drn_{uuid4().hex}")
    status: RunStatus = RunStatus.DRAFT
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    evidence_pack: EvidencePack | None = None
    budget_id: str | None = None
    trajectory_id: str | None = None
    audit_bundle_id: str | None = None
    branches: list[DecisionBranch] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    recommendation: str | None = None
    confidence: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    def attach_evidence_pack(self, evidence_pack: EvidencePack) -> None:
        self.evidence_pack = evidence_pack
        self.touch()

    def add_branch(self, role: str, thesis: str) -> DecisionBranch:
        branch = DecisionBranch(role=role, thesis=thesis)
        self.branches.append(branch)
        self.touch()
        return branch

    def add_assumption(self, text: str, *, importance: str = "medium") -> Assumption:
        assumption = Assumption(text=text, importance=importance)
        self.assumptions.append(assumption)
        self.touch()
        return assumption

    def add_contradiction(self, description: str, *, severity: str = "medium") -> Contradiction:
        contradiction = Contradiction(description=description, severity=severity)
        self.contradictions.append(contradiction)
        self.touch()
        return contradiction

    def mark_running(self) -> None:
        self.status = RunStatus.RUNNING
        self.touch()

    def mark_waiting_for_review(self) -> None:
        self.status = RunStatus.WAITING_FOR_REVIEW
        self.touch()

    def complete(self, *, recommendation: str, confidence: float | None = None) -> None:
        self.recommendation = recommendation
        self.confidence = confidence
        self.status = RunStatus.COMPLETED
        self.touch()


def create_decision_run(
    question: str,
    *,
    domain: str = "general",
    risk_level: str = "unknown",
    execution_mode: str = "deep",
) -> DecisionRun:
    """Factory used by APIs, examples, and tests."""

    return DecisionRun(
        question=question,
        domain=domain,
        risk_level=risk_level,
        execution_mode=execution_mode,
    )
