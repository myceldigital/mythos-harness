from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.json_utils import (
    clamp_confidence,
    compact_text_block,
    ensure_string_list,
    safe_json_parse,
    serialize_json,
)
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
        response = await self.provider.complete(
            model=self.settings.model_base,
            messages=[
                {
                    "role": "user",
                    "content": self._solve_prompt(state, top.answer),
                }
            ],
            max_tokens=700,
            temperature=0.2,
        )
        fallback = {
            "answer": top.answer,
            "reasoning_steps": top.reasoning_path[-3:],
            "confidence": min(0.99, top.confidence + 0.08),
        }
        parsed = safe_json_parse(response["content"], fallback)
        revised_answer = str(parsed.get("answer", "")).strip()
        if revised_answer:
            top.answer = revised_answer
        top.reasoning_path.extend([f"phase.solve::{step}" for step in ensure_string_list(parsed.get("reasoning_steps"))[:2]])
        top.reasoning_path.append("phase.solve")
        top.confidence = clamp_confidence(parsed.get("confidence"), fallback["confidence"])
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
                    "content": self._verify_prompt(state, top.answer),
                }
            ],
            max_tokens=500,
            temperature=0.1,
        )
        parsed = safe_json_parse(
            response["content"],
            {
                "passes": "pass" in response["content"].lower(),
                "issues": [],
                "missing_checks": [],
                "confidence_adjustment": 0.08 if "pass" in response["content"].lower() else -0.2,
                "summary": response["content"],
            },
        )
        passes = bool(parsed.get("passes"))
        issues = ensure_string_list(parsed.get("issues"))
        missing_checks = ensure_string_list(parsed.get("missing_checks"))
        summary = compact_text_block([str(parsed.get("summary", "")).strip(), *issues, *missing_checks]) or response["content"]
        state.structured_state.artifacts.append(
            VerificationArtifact(
                kind="judge_result",
                content=summary,
                passes=passes,
                loop_produced=state.loop_index,
            )
        )
        confidence_adjustment = float(parsed.get("confidence_adjustment", 0.0) or 0.0)
        if not passes:
            for issue in issues or ["judge_failure"]:
                state.structured_state.contradictions.append(
                    Contradiction(
                        claim_a="top_hypothesis",
                        claim_b=issue,
                        severity=0.75,
                        loop_detected=state.loop_index,
                    )
                )
                top.contradictions.append(issue)
            top.confidence = max(0.0, min(0.99, top.confidence + confidence_adjustment))
        else:
            top.supporting_tests.append("judge.pass")
            top.confidence = max(0.0, min(0.99, top.confidence + confidence_adjustment))
        state.structured_state.confidence_map[top.id] = top.confidence

    async def _repair(self, state: MythosState) -> None:
        top = state.structured_state.top_hypothesis()
        if top is None:
            return
        active_issues = [c.claim_b for c in state.structured_state.contradictions if c.loop_detected <= state.loop_index]
        if not active_issues:
            state.structured_state.confidence_map[top.id] = top.confidence
            return
        response = await self.provider.complete(
            model=self.settings.model_base,
            messages=[
                {
                    "role": "user",
                    "content": self._repair_prompt(state, top.answer, active_issues),
                }
            ],
            max_tokens=700,
            temperature=0.2,
        )
        parsed = safe_json_parse(
            response["content"],
            {
                "answer": top.answer,
                "resolved_issues": active_issues,
                "reasoning_steps": ["Explicitly addressed the judge issues before finalizing."],
                "confidence": min(0.99, top.confidence + 0.06),
            },
        )
        repaired_answer = str(parsed.get("answer", "")).strip()
        if repaired_answer:
            top.answer = repaired_answer
        top.reasoning_path.append("phase.repair")
        top.supporting_tests.extend([f"repair::{item}" for item in ensure_string_list(parsed.get("resolved_issues"))])
        top.confidence = clamp_confidence(parsed.get("confidence"), min(0.99, top.confidence + 0.06))
        state.structured_state.contradictions = [
            contradiction
            for contradiction in state.structured_state.contradictions
            if contradiction.claim_b not in set(ensure_string_list(parsed.get("resolved_issues")))
        ]
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
        contradiction_load = len(state.structured_state.contradictions)
        trace_marker = f"top::{top.id}::{round(top.confidence, 2)}::c{contradiction_load}"
        state.structured_state.trace.append(trace_marker)
        return (trace_marker in previous and contradiction_load == 0) or (
            top.confidence >= 0.88 and contradiction_load == 0
        )

    def _solve_prompt(self, state: MythosState, current_answer: str) -> str:
        payload = {
            "query": state.query,
            "current_answer": current_answer,
            "facts": [fact.claim for fact in state.structured_state.facts[-6:]],
            "assumptions": [assumption.statement for assumption in state.structured_state.assumptions[-4:]],
            "contradictions": [c.claim_b for c in state.structured_state.contradictions[-4:]],
        }
        return (
            "Refine the current answer. Return JSON only with keys: answer, reasoning_steps, confidence. "
            "Make the answer query-specific, cite the decisive facts in the wording, and check for logic-trap ordering mistakes.\n\n"
            f"STATE:\n{serialize_json(payload)}"
        )

    def _verify_prompt(self, state: MythosState, answer: str) -> str:
        payload = {
            "query": state.query,
            "answer": answer,
            "facts": [fact.claim for fact in state.structured_state.facts[-6:]],
            "assumptions": [assumption.statement for assumption in state.structured_state.assumptions[-4:]],
        }
        return (
            "Verify the answer for rule-order mistakes, hidden condition traps, overlooked contradictions, and unsupported leaps. "
            "Return JSON only with keys: passes, issues, missing_checks, confidence_adjustment, summary.\n\n"
            f"STATE:\n{serialize_json(payload)}"
        )

    def _repair_prompt(self, state: MythosState, answer: str, issues: list[str]) -> str:
        payload = {
            "query": state.query,
            "answer": answer,
            "issues": issues,
            "facts": [fact.claim for fact in state.structured_state.facts[-6:]],
            "assumptions": [assumption.statement for assumption in state.structured_state.assumptions[-4:]],
        }
        return (
            "Repair the answer using the issues list. Return JSON only with keys: answer, resolved_issues, reasoning_steps, confidence. "
            "Resolve contradictions explicitly and avoid boilerplate.\n\n"
            f"STATE:\n{serialize_json(payload)}"
        )
