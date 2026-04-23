from __future__ import annotations

import json

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
        prompt = messages[-1]["content"].lower()
        if "classify this request for triage" in prompt:
            return {"content": json.dumps(self._triage_response(prompt))}
        if "generate an alternative hypothesis" in prompt:
            return {
                "content": "Alternative hypothesis: prefer phased rollout with metrics guardrails."
            }
        if "judge this hypothesis" in prompt:
            return {"content": "PASS: reasoning is internally consistent and actionable."}
        if "safety revise" in prompt:
            return {"content": "Response revised for policy compliance."}
        if "style harmonize" in prompt:
            return {"content": messages[-1]["content"]}
        return {"content": "Deterministic provider response."}

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
