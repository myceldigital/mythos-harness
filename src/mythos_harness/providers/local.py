from __future__ import annotations

import json
import re
from typing import Any, AsyncIterator

from mythos_harness.providers.base import ModelProvider


class LocalDeterministicProvider(ModelProvider):
    """Deterministic fallback provider for local scaffold runs."""

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, str]:
        _ = (model, max_tokens, temperature)
        raw_prompt = messages[-1]["content"]
        prompt = raw_prompt.lower()
        if "classify this request for triage" in prompt:
            return {"content": json.dumps(self._triage_response(prompt))}
        if "structured prelude extraction" in prompt or "seed mythos structured state" in prompt:
            return {"content": json.dumps(self._prelude_response(raw_prompt))}
        if "generate an alternative hypothesis" in prompt:
            return {
                "content": "Alternative hypothesis: test the opposite reading and compare it against the stated constraints."
            }
        if "refine the current answer" in prompt:
            return {"content": json.dumps(self._solve_response(raw_prompt))}
        if "verify the answer for rule-order mistakes" in prompt:
            return {"content": json.dumps(self._verify_response(raw_prompt))}
        if "repair the answer using the issues list" in prompt:
            return {"content": json.dumps(self._repair_response(raw_prompt))}
        if "safety revise" in prompt:
            return {"content": "Response revised for policy compliance."}
        if "write the final user-facing answer" in prompt:
            return {"content": self._final_response(raw_prompt)}
        return {"content": "Deterministic provider response."}

    async def stream_complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> AsyncIterator[str]:
        response = await self.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        for chunk in _chunk_text(response["content"]):
            yield chunk

    def _triage_response(self, prompt: str) -> dict[str, object]:
        task_type = "analysis"
        if "code" in prompt or "debug" in prompt:
            task_type = "code"
        elif "plan" in prompt:
            task_type = "planning"
        elif "math" in prompt:
            task_type = "math"

        difficulty = 0.45
        ambiguity = 0.35
        execution_mode = "normal"
        if "complex" in prompt or "full" in prompt:
            difficulty = 0.78
            ambiguity = 0.52
            execution_mode = "deep"

        return {
            "task_type": task_type,
            "difficulty": difficulty,
            "ambiguity": ambiguity,
            "risk_domain": None,
            "execution_mode": execution_mode,
            "estimated_cost_tokens": 2800,
            "needs_tools": True,
            "needs_retrieval": True,
        }

    def _prelude_response(self, raw_prompt: str) -> dict[str, Any]:
        query = _extract_json_suffix_value(raw_prompt, "query") or "the user request"
        lowered = query.lower()
        facts = [
            {"claim": query, "source": "query_surface", "confidence": 0.96},
        ]
        assumptions: list[dict[str, Any]] = []
        contradictions: list[dict[str, Any]] = []
        reasoning_steps = [
            "List the controlling facts before drawing a conclusion.",
            "Check whether the prompt hides an ordering or exception trap.",
        ]
        candidate_answer = f"Provisional answer for: {query}"
        confidence = 0.58

        if "aurora" in lowered or "ruling" in lowered:
            assumptions.append(
                {
                    "statement": "The ruling may hinge on which rule controls when two plausible readings conflict.",
                    "rationale": "logic_trap_guard",
                }
            )
            candidate_answer = (
                f"For {query}, first identify the governing rule and then test any tempting but lower-priority reading against it."
            )
            confidence = 0.62
        elif "bullet" in lowered or "3 bullet" in lowered:
            candidate_answer = (
                "Compounding systems outperform one-off effort because they build reusable leverage, improve with feedback, and keep producing value after each iteration."
            )
        elif "migration plan" in lowered or "plan" in lowered:
            facts.append({"claim": "A good plan should sequence work, risks, and validation.", "source": "heuristic", "confidence": 0.74})
            candidate_answer = (
                "Start with current-state audit, then sequence migration steps, validation checkpoints, and rollback criteria."
            )
        return {
            "facts": facts,
            "assumptions": assumptions,
            "contradictions": contradictions,
            "candidate_answer": candidate_answer,
            "reasoning_steps": reasoning_steps,
            "confidence": confidence,
        }

    def _solve_response(self, raw_prompt: str) -> dict[str, Any]:
        state = _extract_embedded_json(raw_prompt)
        query = str(state.get("query", "the task"))
        current_answer = str(state.get("current_answer", ""))
        answer = current_answer or f"Working answer for {query}"
        reasoning_steps = [
            "Ground the answer in the strongest facts from the prompt.",
            "Reject conclusions that depend on skipping rule order or conditions.",
        ]
        if "aurora" in query.lower() or "ruling" in query.lower():
            answer = (
                f"For {query}, the correct path is to apply the controlling rule in order, then check whether any exception actually triggers before stating the ruling."
            )
        return {
            "answer": answer,
            "reasoning_steps": reasoning_steps,
            "confidence": 0.72,
        }

    def _verify_response(self, raw_prompt: str) -> dict[str, Any]:
        state = _extract_embedded_json(raw_prompt)
        answer = str(state.get("answer", ""))
        lowered = answer.lower()
        issues: list[str] = []
        if any(token in lowered for token in ["intuitive", "guess", "shortcut"]):
            issues.append("answer_relies_on_shortcut")
        passes = not issues
        return {
            "passes": passes,
            "issues": issues,
            "missing_checks": [] if passes else ["re-check controlling rule order"],
            "confidence_adjustment": 0.08 if passes else -0.18,
            "summary": "Passes deterministic verification." if passes else "Needs repair to remove shortcut reasoning.",
        }

    def _repair_response(self, raw_prompt: str) -> dict[str, Any]:
        state = _extract_embedded_json(raw_prompt)
        query = str(state.get("query", "the task"))
        issues = [str(item) for item in state.get("issues", []) if str(item)]
        answer = str(state.get("answer", ""))
        if issues:
            answer = (
                f"Repaired answer for {query}: apply the controlling rule explicitly, resolve exceptions in order, and only then state the conclusion."
            )
        return {
            "answer": answer,
            "resolved_issues": issues,
            "reasoning_steps": ["Removed shortcut reasoning and made the governing checks explicit."],
            "confidence": 0.78 if issues else 0.74,
        }

    def _final_response(self, raw_prompt: str) -> str:
        synthesis = _extract_embedded_json(raw_prompt, marker="SYNTHESIS:")
        user_query = _extract_block(raw_prompt, "USER QUERY:") or str(synthesis.get("query", "the request"))
        best_answer = str(synthesis.get("best_answer", "")).strip()
        if "bullet" in user_query.lower() or "3 bullet" in user_query.lower():
            return "- Reusable systems compound output over time.\n- Each cycle improves the system instead of restarting from zero.\n- Gains persist, so future effort produces more leverage."
        return best_answer or f"Answer: {user_query}"


def _extract_block(text: str, marker: str) -> str:
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].strip()


def _extract_embedded_json(text: str, marker: str = "STATE:") -> dict[str, Any]:
    block = _extract_block(text, marker)
    if not block:
        return {}
    start = block.find("{")
    if start == -1:
        return {}
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(block)):
        char = block[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(block[start : idx + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def _extract_json_suffix_value(text: str, key: str) -> str:
    payload = _extract_embedded_json(text, marker="CONTEXT:")
    value = payload.get(key)
    if value is not None:
        return str(value)

    if key == "query":
        match = re.search(r"QUERY:\s*(.*?)(?:\n\n[A-Z_]+:|\Z)", text, re.DOTALL)
        if match:
            return match.group(1).strip()
    return ""


def _chunk_text(text: str, *, size: int = 20) -> list[str]:
    if not text:
        return []
    chunks: list[str] = []
    for idx in range(0, len(text), size):
        chunks.append(text[idx : idx + size])
    return chunks
