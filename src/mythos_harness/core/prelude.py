from __future__ import annotations

import hashlib

from mythos_harness.core.state import GroundedFact, Hypothesis, MythosState


class PreludeBuilder:
    """Builds initial structured state from user input."""

    async def run(self, state: MythosState) -> MythosState:
        digest = hashlib.sha256(state.query.encode("utf-8")).hexdigest()[:10]
        state.encoded_input = f"encoded::{digest}::{state.query[:120]}"
        state.beta = min(
            0.95,
            0.2 + 0.3 * float(state.triage.get("difficulty", 0.5)) + 0.2 * float(state.triage.get("ambiguity", 0.5)),
        )

        state.structured_state.facts.append(
            GroundedFact(
                claim=state.query,
                source="user_input",
                confidence=1.0,
                loop_introduced=0,
            )
        )
        for idx, memory in enumerate(state.retrieved_memories):
            top = memory.top_hypothesis()
            if top is None:
                continue
            state.structured_state.facts.append(
                GroundedFact(
                    claim=f"Retrieved memory hypothesis: {top.answer[:320]}",
                    source=f"memory_similarity:{idx}",
                    confidence=min(0.95, top.confidence),
                    loop_introduced=0,
                )
            )
        state.structured_state.hypotheses.append(
            Hypothesis(
                id=f"h0-{digest}",
                answer="Initial hypothesis: solve with structured phase loop and explicit verification.",
                reasoning_path=["prelude.seed"],
                confidence=0.42,
            )
        )
        state.structured_state.confidence_map["initial"] = 0.42
        return state
