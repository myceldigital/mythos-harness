from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class LoopPhase(str, Enum):
    EXPLORE = "explore"
    SOLVE = "solve"
    VERIFY = "verify"
    REPAIR = "repair"
    SYNTHESIZE = "synthesize"


@dataclass
class GroundedFact:
    claim: str
    source: str
    confidence: float
    loop_introduced: int


@dataclass
class Assumption:
    statement: str
    rationale: str
    resolved: bool = False
    resolution: str | None = None


@dataclass
class Hypothesis:
    id: str
    answer: str
    reasoning_path: list[str]
    confidence: float
    contradictions: list[str] = field(default_factory=list)
    supporting_tests: list[str] = field(default_factory=list)
    alive: bool = True


@dataclass
class Contradiction:
    claim_a: str
    claim_b: str
    severity: float
    loop_detected: int


@dataclass
class VerificationArtifact:
    kind: str
    content: str
    passes: bool
    loop_produced: int


@dataclass
class StructuredState:
    facts: list[GroundedFact] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    artifacts: list[VerificationArtifact] = field(default_factory=list)
    trace: list[str] = field(default_factory=list)
    confidence_map: dict[str, float] = field(default_factory=dict)

    def active_hypotheses(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.alive]

    def should_branch(self) -> bool:
        top = self.active_hypotheses()
        if len(top) >= 3:
            return False
        if any(c.severity > 0.6 for c in self.contradictions):
            return True
        if top and max(h.confidence for h in top) < 0.5:
            return True
        return len(top) <= 1

    def top_hypothesis(self) -> Hypothesis | None:
        live = self.active_hypotheses()
        if not live:
            return None
        return max(live, key=lambda item: item.confidence)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(payload: dict[str, Any]) -> "StructuredState":
        return StructuredState(
            facts=[GroundedFact(**item) for item in payload.get("facts", [])],
            assumptions=[Assumption(**item) for item in payload.get("assumptions", [])],
            hypotheses=[Hypothesis(**item) for item in payload.get("hypotheses", [])],
            contradictions=[
                Contradiction(**item) for item in payload.get("contradictions", [])
            ],
            artifacts=[
                VerificationArtifact(**item) for item in payload.get("artifacts", [])
            ],
            trace=list(payload.get("trace", [])),
            confidence_map=dict(payload.get("confidence_map", {})),
        )


@dataclass
class MythosState:
    query: str
    thread_id: str
    constraints: dict[str, Any] = field(default_factory=dict)
    triage: dict[str, Any] = field(default_factory=dict)
    encoded_input: str = ""
    beta: float = 0.0
    structured_state: StructuredState = field(default_factory=StructuredState)
    retrieved_memories: list[StructuredState] = field(default_factory=list)
    phase: LoopPhase = LoopPhase.EXPLORE
    loop_index: int = 0
    max_loops: int = 6
    converged: bool = False
    halt_reason: str = ""
    final_answer: str = ""
    citations: list[str] = field(default_factory=list)
    confidence_summary: dict[str, float] = field(default_factory=dict)
    per_loop_metrics: list[dict[str, Any]] = field(default_factory=list)
    trajectory_id: str | None = None

    def advance_phase(self) -> None:
        order = [
            LoopPhase.EXPLORE,
            LoopPhase.SOLVE,
            LoopPhase.VERIFY,
            LoopPhase.REPAIR,
            LoopPhase.SYNTHESIZE,
        ]
        idx = order.index(self.phase)
        self.phase = order[(idx + 1) % len(order)]

    def should_halt(self, confidence_threshold: float) -> bool:
        top = self.structured_state.top_hypothesis()
        top_confidence = top.confidence if top else 0.0
        if self.loop_index >= self.max_loops:
            self.halt_reason = "max_loops"
            return True
        if self.converged and top_confidence >= confidence_threshold:
            self.halt_reason = "converged_confident"
            return True
        return False
