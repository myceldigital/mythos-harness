from __future__ import annotations

from mythos_harness.config import Settings
from mythos_harness.core.branch_manager import BranchManager
from mythos_harness.core.coda import CodaBuilder
from mythos_harness.core.feedback import FeedbackLoop
from mythos_harness.core.loop import PhaseLoop
from mythos_harness.core.prelude import PreludeBuilder
from mythos_harness.core.safety import SafetyGate
from mythos_harness.core.state import MythosState
from mythos_harness.core.triage import FrontDoorTriage
from mythos_harness.graph.builder import build_runtime_graph
from mythos_harness.providers.base import ModelProvider
from mythos_harness.storage.contracts import (
    PolicyStoreContract,
    SessionStoreContract,
    TrajectoryStoreContract,
)
from mythos_harness.storage.policy import PolicyStore
from mythos_harness.storage.session import SessionStore
from mythos_harness.storage.trajectory import TrajectoryStore


class MythosOrchestrator:
    def __init__(
        self,
        settings: Settings,
        provider: ModelProvider,
        *,
        session_store: SessionStoreContract | None = None,
        policy_store: PolicyStoreContract | None = None,
        trajectory_store: TrajectoryStoreContract | None = None,
    ):
        self.settings = settings
        self.provider = provider
        self.sessions = session_store or SessionStore()
        self.trajectory_store = trajectory_store or TrajectoryStore(
            settings.trajectory_store_path
        )
        self.policy_store = policy_store or PolicyStore(settings.policy_path)
        self.branch_manager = BranchManager(max_branches=settings.max_branches)
        self.triage = FrontDoorTriage()
        self.prelude = PreludeBuilder()
        self.phase_loop = PhaseLoop(provider, self.branch_manager, settings)
        self.coda = CodaBuilder(provider, self.branch_manager, settings)
        self.safety = SafetyGate(self.policy_store, provider, settings)
        self.feedback = FeedbackLoop(self.trajectory_store)
        self.graph = build_runtime_graph(
            settings=settings,
            provider=provider,
            triage=self.triage,
            prelude=self.prelude,
            phase_loop=self.phase_loop,
            coda=self.coda,
            safety=self.safety,
            feedback=self.feedback,
        )

    async def complete(
        self,
        *,
        query: str,
        thread_id: str,
        constraints: dict[str, object] | None = None,
    ) -> MythosState:
        prior = await self.sessions.get(thread_id)
        runtime = MythosState(
            query=query,
            thread_id=thread_id,
            constraints=constraints or {},
            max_loops=self.settings.max_loops,
        )
        if prior is not None:
            runtime.structured_state = prior
        runtime.retrieved_memories = await self.sessions.search_similar(
            query,
            limit=self.settings.memory_retrieval_k,
            exclude_thread_id=thread_id,
        )

        result = await self.graph.ainvoke({"runtime": runtime})
        final_state: MythosState = result["runtime"]
        await self.sessions.put(thread_id, final_state.structured_state)
        return final_state

    async def readiness(self) -> dict[str, object]:
        session_ok, session_msg = await self.sessions.healthcheck()
        policy_ok, policy_msg = await self.policy_store.healthcheck()
        traj_ok, traj_msg = await self.trajectory_store.healthcheck()
        checks = {
            "session_store": {"ok": session_ok, "detail": session_msg},
            "policy_store": {"ok": policy_ok, "detail": policy_msg},
            "trajectory_store": {"ok": traj_ok, "detail": traj_msg},
        }
        overall = session_ok and policy_ok and traj_ok
        return {"ok": overall, "checks": checks}
