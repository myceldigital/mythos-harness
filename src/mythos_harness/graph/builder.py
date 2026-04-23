from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from mythos_harness.config import Settings
from mythos_harness.core.coda import CodaBuilder
from mythos_harness.core.feedback import FeedbackLoop
from mythos_harness.core.loop import PhaseLoop
from mythos_harness.core.prelude import PreludeBuilder
from mythos_harness.core.state import MythosState
from mythos_harness.core.triage import FrontDoorTriage
from mythos_harness.core.safety import SafetyGate
from mythos_harness.providers.base import ModelProvider


class GraphPayload(TypedDict):
    runtime: MythosState


def build_runtime_graph(
    *,
    settings: Settings,
    provider: ModelProvider,
    triage: FrontDoorTriage,
    prelude: PreludeBuilder,
    phase_loop: PhaseLoop,
    coda: CodaBuilder,
    safety: SafetyGate,
    feedback: FeedbackLoop,
):
    graph = StateGraph(GraphPayload)

    async def front_door(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        state.triage = await triage.triage(state.query, provider, settings)
        if state.triage.get("execution_mode") == "exhaustive":
            state.max_loops = max(state.max_loops, settings.max_loops + 2)
        return {"runtime": state}

    async def prelude_node(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        await prelude.run(state)
        return {"runtime": state}

    async def loop_node(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        if state.should_halt(settings.default_confidence_threshold):
            return {"runtime": state}
        await phase_loop.run_current_phase(state)
        state.should_halt(settings.default_confidence_threshold)
        return {"runtime": state}

    async def coda_node(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        if not state.halt_reason:
            state.halt_reason = "graph_exit"
        await coda.run(state)
        return {"runtime": state}

    async def safety_node(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        await safety.apply(state)
        return {"runtime": state}

    async def feedback_node(payload: GraphPayload) -> GraphPayload:
        state = payload["runtime"]
        state.trajectory_id = await feedback.log_trajectory(state)
        return {"runtime": state}

    def loop_router(payload: GraphPayload) -> str:
        state = payload["runtime"]
        if state.should_halt(settings.default_confidence_threshold):
            return "coda"
        return "loop"

    graph.add_node("front_door", front_door)
    graph.add_node("prelude", prelude_node)
    graph.add_node("loop", loop_node)
    graph.add_node("coda", coda_node)
    graph.add_node("safety", safety_node)
    graph.add_node("feedback", feedback_node)

    graph.add_edge(START, "front_door")
    graph.add_edge("front_door", "prelude")
    graph.add_edge("prelude", "loop")
    graph.add_conditional_edges("loop", loop_router, {"loop": "loop", "coda": "coda"})
    graph.add_edge("coda", "safety")
    graph.add_edge("safety", "feedback")
    graph.add_edge("feedback", END)

    return graph.compile()
