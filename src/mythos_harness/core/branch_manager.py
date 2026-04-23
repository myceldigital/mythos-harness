from __future__ import annotations

import hashlib

from mythos_harness.core.state import Hypothesis, StructuredState
from mythos_harness.providers.base import ModelProvider


class BranchManager:
    """Maintains competing hypotheses and prunes weak branches."""

    def __init__(self, max_branches: int = 3):
        self.max_branches = max_branches

    async def step(self, state: StructuredState, provider: ModelProvider) -> StructuredState:
        if state.should_branch() and len(state.active_hypotheses()) < self.max_branches:
            new_hypothesis = await self._generate_alternative(state, provider)
            state.hypotheses.append(new_hypothesis)

        for hypothesis in state.hypotheses:
            if hypothesis.confidence < 0.2 or len(hypothesis.contradictions) >= 3:
                hypothesis.alive = False
        return state

    async def collapse(self, state: StructuredState) -> Hypothesis:
        alive = state.active_hypotheses()
        if not alive:
            raise RuntimeError("No live hypotheses at collapse time")
        return max(alive, key=lambda h: h.confidence * (1 - 0.1 * len(h.contradictions)))

    async def _generate_alternative(
        self, state: StructuredState, provider: ModelProvider
    ) -> Hypothesis:
        basis = state.top_hypothesis().answer if state.top_hypothesis() else "No basis hypothesis."
        response = await provider.complete(
            model="branch-alt",
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate an alternative hypothesis. "
                        f"Current top hypothesis: {basis}"
                    ),
                }
            ],
            max_tokens=220,
            temperature=0.6,
        )
        seed = hashlib.sha256(response["content"].encode("utf-8")).hexdigest()[:8]
        return Hypothesis(
            id=f"h-{seed}",
            answer=response["content"],
            reasoning_path=["explore.branch_manager"],
            confidence=0.38,
        )
