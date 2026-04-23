from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.core.state import MythosState
from mythos_harness.providers.base import ModelProvider
from mythos_harness.storage.contracts import PolicyStoreContract


class SafetyGate:
    def __init__(
        self,
        policy_store: PolicyStoreContract,
        provider: ModelProvider,
        settings: Settings,
    ) -> None:
        self.policy_store = policy_store
        self.provider = provider
        self.settings = settings

    async def apply(self, state: MythosState) -> MythosState:
        policies = await self.policy_store.load()
        answer_lc = state.final_answer.lower()
        blocked_terms = policies.get("blocked_terms", [])
        revision_terms = policies.get("revision_required_terms", [])

        if any(term.lower() in answer_lc for term in blocked_terms):
            state.final_answer = "Response withheld due to policy constraints."
            return state

        if any(term.lower() in answer_lc for term in revision_terms):
            revised = await self.provider.complete(
                model=self.settings.model_fast,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Safety revise this response to remove policy-sensitive content "
                            "while preserving useful safe detail:\n\n"
                            f"{state.final_answer}"
                        ),
                    }
                ],
                max_tokens=600,
                temperature=0.0,
            )
            state.final_answer = revised["content"]
        return state
