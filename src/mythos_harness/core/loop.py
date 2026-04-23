from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.state import Contradiction, LoopPhase, MythosState, VerificationArtifact
from mythos_harness.providers.base import ModelProvider


class PhaseLoop:
    def __init__(
        self,
        provider: ModelProvider,
        branch_manager: BranchManager,
        settings: Settings,
    ) -> None:
        self.provider = provider
        self.branch_manager = branch_manager
        self.settings = settings

    async def run_current_phase(self, state: MythosState) -> MythosState:
        if state.phase == LoopPhase.EXPLORE:
            await self._explore(state)
        elif state.phase == LoopPhase.SOLVE:
            await self._solve(state)
        elif state.phase == LoopPhase.VERIFY:
            await self._verify(state)
        elif state.phase == LoopPhase.REPAIR:
            await self._repair(state)
        else:
            await self._synthesize(state)

        state.loop_index += 1
        state.converged = self._convergence_check(state)
        state.per_loop_metrics.append(
            {
                "loop": state.loop_index,
                "phase": state.phase.value,
                "active_hypotheses": len(state.structured_state.active_hypotheses()),
                "converged": state.converged,
            }
        )
        state.advance_phase()
        return state

    async def _explore(self, state: MythosState) -> None:
        await self.branch_manager.step(state.structured_state, self.provider)
        state.structured_state.trace.append("phase.explore.completed")

    async def _solve(self, state: MythosState) -> None:
        top = state.structured_state.top_hypothesis()
        if top is None:
            return
        top.answer += " Solve pass: include constraints, cost envelope, and tool plan."
        top.reasoning_path.append("phase.solve")
        top.confidence = min(0.99, top.confidence + 0.14)
        state.structured_state.confidence_map[top.id] = top.confidence

    async def _verify(self, state: MythosState) -> None:
        top = state.structured_state.top_hypothesis()
        if top is None:
            return
        response = await self.provider.complete(
            model=self.settings.model_judge,
            messages=[
                {
                    "role": "user",
                    "content": f"Judge this hypothesis for internal consistency:\n\n{top.answer}",
                }
            ],
            max_tokens=220,
            temperature=0.1,
        )
        passed = "pass" in response["content"].lower()
        state.structured_state.artifacts.append(
            VerificationArtifact(
                kind="judge_result",
                content=response["content"],
                passes=passed,
                loop_produced=state.loop_index,
            )
        )
        if not passed:
            state.structured_state.contradictions.append(
                Contradiction(
                    claim_a="top_hypothesis",
                    claim_b="judge_failure",
                    severity=0.8,
                    loop_detected=state.loop_index,
                )
            )
            top.contradictions.append("judge_failure")
            top.confidence = max(0.0, top.confidence - 0.25)
        else:
            top.supporting_tests.append("judge.pass")
            top.confidence = min(0.99, top.confidence + 0.1)
        state.structured_state.confidence_map[top.id] = top.confidence

    async def _repair(self, state: MythosState) -> None:
        top = state.structured_state.top_hypothesis()
        if top is None:
            return
        if state.structured_state.contradictions:
            top.answer += " Repair pass: resolved contradictions with explicit assumptions."
            top.reasoning_path.append("phase.repair")
            top.confidence = min(0.99, top.confidence + 0.08)
        state.structured_state.confidence_map[top.id] = top.confidence

    async def _synthesize(self, state: MythosState) -> None:
        winner = await self.branch_manager.collapse(state.structured_state)
        winner.reasoning_path.append("phase.synthesize")
        state.structured_state.confidence_map[winner.id] = winner.confidence

    def _convergence_check(self, state: MythosState) -> bool:
        top = state.structured_state.top_hypothesis()
        if top is None:
            return False
        if state.loop_index < 2:
            return False
        previous = state.structured_state.trace[-2:] if len(state.structured_state.trace) >= 2 else []
        trace_marker = f"top::{top.id}::{round(top.confidence, 2)}"
        state.structured_state.trace.append(trace_marker)
        return trace_marker in previous or top.confidence >= 0.88
