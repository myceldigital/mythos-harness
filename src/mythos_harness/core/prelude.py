from __future__ import annotations

import hashlib

from mythos_harness.config import Settings
from mythos_harness.core.json_utils import (
    clamp_confidence,
    compact_text_block,
    ensure_dict_list,
    ensure_string_list,
    safe_json_parse,
    serialize_json,
)
from mythos_harness.core.state import Assumption, Contradiction, GroundedFact, Hypothesis, MythosState
from mythos_harness.providers.base import ModelProvider


class PreludeBuilder:
    """Builds initial structured state from user input."""

    def __init__(self, provider: ModelProvider, settings: Settings) -> None:
        self.provider = provider
        self.settings = settings

    async def run(self, state: MythosState) -> MythosState:
        digest = hashlib.sha256(state.query.encode("utf-8")).hexdigest()[:10]
        state.encoded_input = f"encoded::{digest}::{state.query[:120]}"
        state.beta = min(
            0.95,
            0.2 + 0.3 * float(state.triage.get("difficulty", 0.5)) + 0.2 * float(state.triage.get("ambiguity", 0.5)),
        )

        self._append_fact(
            state,
            GroundedFact(
                claim=state.query,
                source="user_input",
                confidence=1.0,
                loop_introduced=0,
            ),
        )
        for idx, memory in enumerate(state.retrieved_memories):
            top = memory.top_hypothesis()
            if top is None:
                continue
            self._append_fact(
                state,
                GroundedFact(
                    claim=f"Retrieved memory hypothesis: {top.answer[:320]}",
                    source=f"memory_similarity:{idx}",
                    confidence=min(0.95, top.confidence),
                    loop_introduced=0,
                ),
            )

        response = await self.provider.complete(
            model=self.settings.model_base,
            messages=[
                {
                    "role": "user",
                    "content": self._build_prompt(state),
                }
            ],
            max_tokens=900,
            temperature=0.15,
        )
        payload = safe_json_parse(response["content"], fallback={})

        candidate_answer = self._apply_payload(state, payload)
        if not candidate_answer:
            candidate_answer = "Initial hypothesis: solve the user query with explicit evidence, assumptions, and verification."

        hypothesis = Hypothesis(
            id=f"h0-{digest}",
            answer=candidate_answer,
            reasoning_path=ensure_string_list(payload.get("reasoning_path")) or ["prelude.seed"],
            confidence=clamp_confidence(payload.get("confidence"), 0.42),
        )
        state.structured_state.hypotheses.append(hypothesis)
        state.structured_state.confidence_map[hypothesis.id] = hypothesis.confidence
        state.structured_state.confidence_map["initial"] = hypothesis.confidence
        state.structured_state.trace.append("phase.prelude.completed")
        return state

    def _build_prompt(self, state: MythosState) -> str:
        memories: list[dict[str, object]] = []
        for idx, memory in enumerate(state.retrieved_memories):
            top = memory.top_hypothesis()
            memories.append(
                {
                    "memory_index": idx,
                    "top_answer": top.answer if top else "",
                    "top_confidence": top.confidence if top else 0.0,
                    "facts": [fact.claim for fact in memory.facts[:3]],
                }
            )

        return (
            "Analyze the user request and seed Mythos structured state. "
            "Return JSON only with this schema: "
            '{"facts":[{"claim":"...","source":"...","confidence":0.0}],'
            '"assumptions":[{"statement":"...","rationale":"..."}],'
            '"contradictions":[{"claim_a":"...","claim_b":"...","severity":0.0}],'
            '"candidate_answer":"...","reasoning_path":["..."],"confidence":0.0}.\n\n'
            f"QUERY:\n{state.query}\n\n"
            f"CONSTRAINTS:\n{serialize_json(state.constraints)}\n\n"
            f"TRIAGE:\n{serialize_json(state.triage)}\n\n"
            f"RETRIEVED_MEMORIES:\n{serialize_json({'memories': memories})}\n\n"
            "Ground facts in the query and retrieved memories. Keep assumptions explicit."
        )

    def _apply_payload(self, state: MythosState, payload: dict[str, object]) -> str:
        for item in ensure_dict_list(payload.get("facts")):
            claim = str(item.get("claim", "")).strip()
            if not claim:
                continue
            self._append_fact(
                state,
                GroundedFact(
                    claim=claim,
                    source=str(item.get("source") or "model_prelude"),
                    confidence=clamp_confidence(item.get("confidence"), 0.6),
                    loop_introduced=0,
                ),
            )

        for item in ensure_dict_list(payload.get("assumptions")):
            statement = str(item.get("statement", "")).strip()
            if not statement:
                continue
            state.structured_state.assumptions.append(
                Assumption(
                    statement=statement,
                    rationale=str(item.get("rationale") or "Model-generated planning assumption.").strip(),
                )
            )

        for item in ensure_dict_list(payload.get("contradictions")):
            claim_a = str(item.get("claim_a", "")).strip()
            claim_b = str(item.get("claim_b", "")).strip()
            if not claim_a or not claim_b:
                continue
            state.structured_state.contradictions.append(
                Contradiction(
                    claim_a=claim_a,
                    claim_b=claim_b,
                    severity=clamp_confidence(item.get("severity"), 0.45),
                    loop_detected=0,
                )
            )

        answer = str(payload.get("candidate_answer") or "").strip()
        if answer:
            return answer

        query_snippet = compact_text_block(state.query.splitlines())[:220]
        return f"Initial hypothesis for query: {query_snippet}"

    @staticmethod
    def _append_fact(state: MythosState, fact: GroundedFact) -> None:
        for existing in state.structured_state.facts:
            if existing.claim == fact.claim and existing.source == fact.source:
                return
        state.structured_state.facts.append(fact)
