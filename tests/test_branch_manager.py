import asyncio

from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.state import Contradiction, Hypothesis, StructuredState
from mythos_harness.providers.local import LocalDeterministicProvider


def test_branch_manager_adds_alternative_when_needed() -> None:
    manager = BranchManager(max_branches=3)
    provider = LocalDeterministicProvider()
    state = StructuredState(
        hypotheses=[
            Hypothesis(
                id="h1",
                answer="baseline",
                reasoning_path=["seed"],
                confidence=0.3,
            )
        ],
        contradictions=[
            Contradiction(
                claim_a="a",
                claim_b="b",
                severity=0.8,
                loop_detected=1,
            )
        ],
    )

    updated = asyncio.run(manager.step(state, provider))
    assert len(updated.hypotheses) >= 2


def test_branch_manager_prunes_bad_hypotheses() -> None:
    manager = BranchManager(max_branches=3)
    provider = LocalDeterministicProvider()
    state = StructuredState(
        hypotheses=[
            Hypothesis(
                id="h1",
                answer="bad",
                reasoning_path=["seed"],
                confidence=0.1,
                contradictions=["c1", "c2", "c3"],
            )
        ]
    )
    updated = asyncio.run(manager.step(state, provider))
    assert updated.hypotheses[0].alive is False
