from __future__ import annotations

from fastapi import APIRouter, Depends

from mythos_harness.api.schemas import CompleteRequest, CompleteResponse
from mythos_harness.core.service import MythosOrchestrator


router = APIRouter(prefix="/v1/mythos", tags=["mythos"])


def get_orchestrator() -> MythosOrchestrator:
    raise RuntimeError("Orchestrator dependency not initialized.")


@router.post("/complete", response_model=CompleteResponse)
async def complete(
    request: CompleteRequest,
    orchestrator: MythosOrchestrator = Depends(get_orchestrator),
) -> CompleteResponse:
    result = await orchestrator.complete(
        query=request.query,
        thread_id=request.thread_id,
        constraints=request.constraints,
    )
    return CompleteResponse(
        thread_id=result.thread_id,
        final_answer=result.final_answer,
        confidence_summary=result.confidence_summary,
        citations=result.citations,
        loops=result.loop_index,
        halt_reason=result.halt_reason,
        trajectory_id=result.trajectory_id,
        triage=result.triage,
    )
