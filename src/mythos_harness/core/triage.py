from __future__ import annotations

from typing import Any

from mythos_harness.config import Settings
from mythos_harness.core.json_utils import extract_first_json_object, safe_json_parse
from mythos_harness.providers.base import ModelProvider


class FrontDoorTriage:
    PROMPT = """Classify this request for triage. Return JSON:
- task_type: one of {default, math, code, literature, analysis, planning, factual}
- difficulty: 0-1
- ambiguity: 0-1
- risk_domain: null | legal | medical | financial | safety | cyber
- execution_mode: fast | normal | deep | exhaustive
- estimated_cost_tokens: int
- needs_tools: bool
- needs_retrieval: bool"""

    async def triage(
        self, query: str, provider: ModelProvider, config: Settings
    ) -> dict[str, Any]:
        response = await provider.complete(
            model=config.model_fast,
            messages=[{"role": "user", "content": f"{self.PROMPT}\n\nQUERY: {query}"}],
            max_tokens=400,
            temperature=0.1,
        )
        return safe_json_parse(
            response["content"],
            fallback={
                "task_type": "default",
                "difficulty": 0.5,
                "ambiguity": 0.5,
                "risk_domain": None,
                "execution_mode": "normal",
                "estimated_cost_tokens": 1600,
                "needs_tools": False,
                "needs_retrieval": False,
            },
        )


__all__ = ["FrontDoorTriage", "extract_first_json_object", "safe_json_parse"]
