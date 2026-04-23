from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime, timezone

from mythos_harness.core.state import MythosState
from mythos_harness.storage.contracts import TrajectoryStoreContract


class FeedbackLoop:
    """Passive logger. Active optimization must remain offline + gated."""

    def __init__(self, storage: TrajectoryStoreContract):
        self.storage = storage

    async def log_trajectory(self, state: MythosState) -> str:
        trajectory_id = hashlib.sha256(
            f"{state.thread_id}:{state.query}".encode("utf-8")
        ).hexdigest()[:12]
        await self.storage.write(
            {
                "id": trajectory_id,
                "query": state.query,
                "thread_id": state.thread_id,
                "final_answer": state.final_answer,
                "loops": state.loop_index,
                "halt_reason": state.halt_reason,
                "per_loop_metrics": state.per_loop_metrics,
                "structured_state": asdict(state.structured_state),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        return trajectory_id

    async def evaluate_batch(self, trajectory_ids: list[str]) -> dict[str, object]:
        _ = trajectory_ids
        return {
            "status": "offline_only",
            "message": "Batch evaluation is intentionally not in the hot path.",
        }
