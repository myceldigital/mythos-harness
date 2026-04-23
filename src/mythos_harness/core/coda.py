from __future__ import annotations

from typing import AsyncIterator

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.state import MythosState
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
                    "content": f"Style harmonize this final answer without changing meaning:\n\n{synthesis}",
                }
            ],
            max_tokens=700,
            temperature=0.2,
        )
        state.final_answer = style_resp["content"]
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
                    "content": f"Style harmonize this final answer without changing meaning:\n\n{synthesis}",
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
        return (
            f"{winner.answer}\n\n"
            f"Execution mode: {state.triage.get('execution_mode', 'normal')}. "
            f"Loops used: {state.loop_index}. Halt reason: {state.halt_reason or 'in_progress'}."
        )

    def _finalize_metadata(self, state: MythosState) -> None:
        state.citations = [f.source for f in state.structured_state.facts if f.source != "user_input"]
        top = state.structured_state.top_hypothesis()
        state.confidence_summary = {
            "top_hypothesis": top.confidence if top else 0.0,
            "overall": min(
                0.99,
                0.55
                + 0.25 * (1.0 if state.converged else 0.0)
                + 0.2 * (top.confidence if top else 0.0),
            ),
        }
