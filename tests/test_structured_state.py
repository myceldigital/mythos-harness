from mythos_harness.core.state import Hypothesis, LoopPhase, MythosState, StructuredState


def test_should_branch_when_single_low_conf_hypothesis() -> None:
    state = StructuredState(
        hypotheses=[
            Hypothesis(
                id="h1",
                answer="x",
                reasoning_path=["seed"],
                confidence=0.3,
            )
        ]
    )
    assert state.should_branch() is True


def test_should_not_branch_when_three_live_hypotheses() -> None:
    state = StructuredState(
        hypotheses=[
            Hypothesis(id="h1", answer="a", reasoning_path=["x"], confidence=0.5),
            Hypothesis(id="h2", answer="b", reasoning_path=["x"], confidence=0.5),
            Hypothesis(id="h3", answer="c", reasoning_path=["x"], confidence=0.5),
        ]
    )
    assert state.should_branch() is False


def test_mythos_state_halts_on_loop_cap() -> None:
    runtime = MythosState(query="q", thread_id="t", max_loops=1, phase=LoopPhase.EXPLORE)
    runtime.loop_index = 1
    assert runtime.should_halt(0.75) is True
    assert runtime.halt_reason == "max_loops"
