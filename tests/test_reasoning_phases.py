import asyncio
import json

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.coda import CodaBuilder
from mythos_harness.core.loop import PhaseLoop
from mythos_harness.core.prelude import PreludeBuilder
from mythos_harness.core.state import GroundedFact, Hypothesis, LoopPhase, MythosState
from mythos_harness.providers.base import ModelProvider


class ScriptedProvider(ModelProvider):
    def __init__(self, responses: dict[str, str]) -> None:
        self.responses = responses

    async def complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> dict[str, str]:
        _ = (model, max_tokens, temperature)
        prompt = messages[-1]["content"]
        for key, response in self.responses.items():
            if key in prompt:
                return {"content": response}
        raise AssertionError(f"Unexpected prompt: {prompt}")

    async def stream_complete(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> object:
        response = await self.complete(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        yield response["content"]


def test_prelude_parses_query_aware_fenced_json() -> None:
    provider = ScriptedProvider(
        {
            "Analyze the user request and seed Mythos structured state": (
                "```json\n"
                + json.dumps(
                    {
                        "facts": [
                            {
                                "claim": "The user asked for exactly three bullets.",
                                "source": "query_format",
                                "confidence": 0.92,
                            }
                        ],
                        "assumptions": [
                            {
                                "statement": "The answer should stay concise.",
                                "rationale": "User asked for bullets rather than prose.",
                            }
                        ],
                        "contradictions": [],
                        "candidate_answer": "Use three concise bullets about why compounding matters.",
                        "reasoning_path": ["extract_format", "extract_topic"],
                        "confidence": 0.67,
                    }
                )
                + "\n```"
            )
        }
    )
    settings = Settings(_env_file=None, provider_backend="local")
    prelude = PreludeBuilder(provider, settings)
    state = MythosState(
        query="Give exactly 3 bullet points on why compounding systems matter.",
        thread_id="thread-1",
        constraints={"format": "3 bullets"},
        triage={"difficulty": 0.4, "ambiguity": 0.2},
    )

    runtime = asyncio.run(prelude.run(state))

    top = runtime.structured_state.top_hypothesis()
    assert top is not None
    assert top.answer == "Use three concise bullets about why compounding matters."
    assert top.reasoning_path[:2] == ["extract_format", "extract_topic"]
    assert any(fact.source == "query_format" for fact in runtime.structured_state.facts)
    assert runtime.structured_state.assumptions[0].statement == "The answer should stay concise."


def test_phase_loop_verify_and_repair_propagate_corrections() -> None:
    provider = ScriptedProvider(
        {
            "Refine the current answer": json.dumps(
                {
                    "answer": "Shortcut answer that sounds intuitive but skips the controlling rule.",
                    "reasoning_steps": ["Summarize the most likely reading first."],
                    "confidence": 0.7,
                }
            ),
            "Verify the answer for rule-order mistakes": json.dumps(
                {
                    "passes": False,
                    "issues": ["answer_relies_on_shortcut"],
                    "missing_checks": ["check controlling rule order"],
                    "confidence_adjustment": -0.3,
                    "summary": "The answer jumps to the intuitive reading before applying the controlling rule.",
                }
            ),
            "Repair the answer using the issues list": json.dumps(
                {
                    "answer": "Corrected answer that applies the controlling rule first and only then states the conclusion.",
                    "resolved_issues": ["answer_relies_on_shortcut"],
                    "reasoning_steps": ["Applied the governing rule before evaluating exceptions."],
                    "confidence": 0.83,
                }
            ),
        }
    )
    settings = Settings(_env_file=None, provider_backend="local")
    loop = PhaseLoop(provider, BranchManager(), settings)
    state = MythosState(query="Solve the Aurora Ruling puzzle.", thread_id="thread-2")
    state.structured_state.facts.append(
        GroundedFact(claim="Rule order matters in the puzzle.", source="puzzle", confidence=0.95, loop_introduced=0)
    )
    state.structured_state.hypotheses.append(
        Hypothesis(id="h1", answer="Initial answer", reasoning_path=["prelude.seed"], confidence=0.55)
    )

    state.phase = LoopPhase.SOLVE
    asyncio.run(loop.run_current_phase(state))
    top = state.structured_state.top_hypothesis()
    assert top is not None
    assert "Shortcut answer" in top.answer
    assert "phase.solve" in top.reasoning_path

    state.phase = LoopPhase.VERIFY
    asyncio.run(loop.run_current_phase(state))
    top = state.structured_state.top_hypothesis()
    assert top is not None
    assert state.structured_state.artifacts[-1].passes is False
    assert state.structured_state.contradictions[-1].claim_b == "answer_relies_on_shortcut"
    assert top.confidence < 0.7

    state.phase = LoopPhase.REPAIR
    asyncio.run(loop.run_current_phase(state))
    top = state.structured_state.top_hypothesis()
    assert top is not None
    assert top.answer.startswith("Corrected answer")
    assert "phase.repair" in top.reasoning_path
    assert not state.structured_state.contradictions
    assert "repair::answer_relies_on_shortcut" in top.supporting_tests


def test_coda_respects_requested_output_shape() -> None:
    provider = ScriptedProvider(
        {
            "Write the final user-facing answer": "- First bullet\n- Second bullet\n- Third bullet"
        }
    )
    settings = Settings(_env_file=None, provider_backend="local")
    coda = CodaBuilder(provider, BranchManager(), settings)
    state = MythosState(
        query="Give exactly 3 bullet points on why compounding systems matter.",
        thread_id="thread-3",
        triage={"execution_mode": "normal"},
        halt_reason="converged_confident",
    )
    state.loop_index = 3
    state.converged = True
    state.structured_state.facts.append(
        GroundedFact(claim="The user requested three bullets.", source="query_format", confidence=1.0, loop_introduced=0)
    )
    state.structured_state.hypotheses.append(
        Hypothesis(
            id="h1",
            answer="Three bullets about compounding systems.",
            reasoning_path=["phase.solve"],
            confidence=0.86,
        )
    )

    runtime = asyncio.run(coda.run(state))

    lines = runtime.final_answer.splitlines()
    assert lines == ["- First bullet", "- Second bullet", "- Third bullet"]
    assert runtime.confidence_summary["overall"] > 0.0


def test_local_deterministic_prelude_reads_query_from_prompt_shape() -> None:
    from mythos_harness.providers.local import LocalDeterministicProvider

    provider = LocalDeterministicProvider()
    settings = Settings(_env_file=None, provider_backend="local")
    prelude = PreludeBuilder(provider, settings)
    state = MythosState(
        query="The Aurora Ruling",
        thread_id="thread-4",
        constraints={},
        triage={"difficulty": 0.6, "ambiguity": 0.4},
    )

    runtime = asyncio.run(prelude.run(state))
    top = runtime.structured_state.top_hypothesis()
    assert top is not None
    assert "Aurora" in top.answer or "ruling" in top.answer.lower()


def test_service_restores_prior_structured_state_for_same_thread() -> None:
    from mythos_harness.core.service import MythosOrchestrator
    from mythos_harness.providers.local import LocalDeterministicProvider
    from mythos_harness.storage.factory import build_storage

    settings = Settings(_env_file=None, provider_backend="local")
    provider = LocalDeterministicProvider()
    stores = build_storage(settings)
    orchestrator = MythosOrchestrator(
        settings=settings,
        provider=provider,
        session_store=stores.sessions,
        policy_store=stores.policy,
        trajectory_store=stores.trajectories,
    )

    prior = runtime_state = MythosState(query="q1", thread_id="thread-5").structured_state
    prior.hypotheses.append(Hypothesis(id="saved", answer="persisted answer", reasoning_path=["seed"], confidence=0.77))
    asyncio.run(stores.sessions.put("thread-5", prior))

    runtime = asyncio.run(orchestrator._initialize_runtime(query="q2", thread_id="thread-5", constraints={}))
    top = runtime.structured_state.top_hypothesis()
    assert top is not None
    assert top.answer == "persisted answer"
    assert runtime.retrieved_memories == []


def test_solve_keeps_reasoning_steps_out_of_answer_text() -> None:
    provider = ScriptedProvider(
        {
            "Refine the current answer": json.dumps(
                {
                    "answer": "Clean final answer.",
                    "reasoning_steps": ["Internal step that should not leak."],
                    "confidence": 0.7,
                }
            )
        }
    )
    settings = Settings(_env_file=None, provider_backend="local")
    loop = PhaseLoop(provider, BranchManager(), settings)
    state = MythosState(query="Answer cleanly.", thread_id="thread-6")
    state.structured_state.hypotheses.append(
        Hypothesis(id="h1", answer="Initial answer", reasoning_path=["seed"], confidence=0.55)
    )
    state.phase = LoopPhase.SOLVE

    asyncio.run(loop.run_current_phase(state))
    top = state.structured_state.top_hypothesis()
    assert top is not None
    assert top.answer == "Clean final answer."
    assert "Internal step that should not leak." not in top.answer
