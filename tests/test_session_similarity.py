import asyncio

from mythos_harness.core.state import Hypothesis, StructuredState
from mythos_harness.storage.session import SessionStore


def test_memory_session_store_similarity_search() -> None:
    store = SessionStore()
    asyncio.run(
        store.put(
            "thread-a",
            StructuredState(
                hypotheses=[
                    Hypothesis(
                        id="h-a",
                        answer="database migration and vector index rollout",
                        reasoning_path=["seed"],
                        confidence=0.7,
                    )
                ]
            ),
        )
    )
    asyncio.run(
        store.put(
            "thread-b",
            StructuredState(
                hypotheses=[
                    Hypothesis(
                        id="h-b",
                        answer="frontend css cleanup task",
                        reasoning_path=["seed"],
                        confidence=0.6,
                    )
                ]
            ),
        )
    )

    results = asyncio.run(
        store.search_similar("need vector migration plan", limit=1, exclude_thread_id="thread-z")
    )
    assert len(results) == 1
    top = results[0].top_hypothesis()
    assert top is not None
    assert "vector" in top.answer
