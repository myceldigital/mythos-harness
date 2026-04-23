from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

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


@router.post("/stream")
async def complete_stream(
    request: CompleteRequest,
    orchestrator: MythosOrchestrator = Depends(get_orchestrator),
) -> StreamingResponse:
    async def event_stream():
        try:
            async for event, payload in orchestrator.complete_stream(
                query=request.query,
                thread_id=request.thread_id,
                constraints=request.constraints,
            ):
                yield _sse_event(event, payload)
            yield _sse_event("done", {"ok": True})
        except Exception as exc:
            yield _sse_event("error", {"message": str(exc)})
            yield _sse_event("done", {"ok": False})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


def _sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"
