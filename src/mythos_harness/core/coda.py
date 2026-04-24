from __future__ import annotations

from typing import AsyncIterator

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.state import MythosState
from mythos_harness.core.json_utils import serialize_json
from mythos_harness.providers.base import ModelProvider


class CodaBuilder:
    def __init__(
        self,
        provider: ModelProvider,
        branch_manager: BranchManager,
        settings: Settings,
    ) -> None:
        self.provider = provider
        self.branch_manager = branch_manager
        self.settings = settings

    async def run(self, state: MythosState) -> MythosState:
        synthesis = await self._build_synthesis(state)
        style_resp = await self.provider.complete(
            model=self.settings.model_style,
            messages=[
                {
                    "role": "user",
                    "content": self._final_prompt(state, synthesis),
                }
            ],
            max_tokens=700,
            temperature=0.2,
        )
        state.final_answer = style_resp["content"].strip()
        self._finalize_metadata(state)
        return state

    async def run_stream(self, state: MythosState) -> AsyncIterator[str]:
        synthesis = await self._build_synthesis(state)
        chunks: list[str] = []
        async for token in self.provider.stream_complete(
            model=self.settings.model_style,
            messages=[
                {
                    "role": "user",
                    "content": self._final_prompt(state, synthesis),
                }
            ],
            max_tokens=700,
            temperature=0.2,
        ):
            chunks.append(token)
            yield token
        state.final_answer = "".join(chunks).strip()
        self._finalize_metadata(state)

    async def _build_synthesis(self, state: MythosState) -> str:
        winner = await self.branch_manager.collapse(state.structured_state)
        facts = [fact.claim for fact in state.structured_state.facts[-6:]]
        assumptions = [assumption.statement for assumption in state.structured_state.assumptions[-4:]]
        contradictions = [c.claim_b for c in state.structured_state.contradictions[-4:]]
        verification = [artifact.content for artifact in state.structured_state.artifacts[-3:]]
        payload = {
            "query": state.query,
            "best_answer": winner.answer,
            "facts": facts,
            "assumptions": assumptions,
            "open_contradictions": contradictions,
            "verification": verification,
            "execution_mode": state.triage.get("execution_mode", "normal"),
            "loops": state.loop_index,
            "halt_reason": state.halt_reason or "in_progress",
        }
        return serialize_json(payload)

    def _final_prompt(self, state: MythosState, synthesis: str) -> str:
        return (
            "Write the final user-facing answer. Use the provided best answer and evidence. "
            "Obey the user's requested format exactly, avoid scaffold/meta commentary, and mention uncertainty only when supported by the evidence.\n\n"
            f"SYNTHESIS:\n{synthesis}\n\nUSER QUERY:\n{state.query}"
        )

    def _finalize_metadata(self, state: MythosState) -> None:
        state.citations = [f.source for f in state.structured_state.facts if f.source != "user_input"]
        top = state.structured_state.top_hypothesis()
        unresolved_penalty = min(0.2, 0.05 * len(state.structured_state.contradictions))
        state.confidence_summary = {
            "top_hypothesis": top.confidence if top else 0.0,
            "overall": max(
                0.0,
                min(
                    0.99,
                    0.5
                    + 0.22 * (1.0 if state.converged else 0.0)
                    + 0.23 * (top.confidence if top else 0.0)
                    - unresolved_penalty,
                ),
            ),
        }
