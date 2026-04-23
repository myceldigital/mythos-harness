from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CompleteRequest(BaseModel):
    query: str = Field(min_length=1, description="User request text.")
    thread_id: str = Field(default="default-thread", description="Conversation/session key.")
    constraints: dict[str, Any] = Field(default_factory=dict)


class CompleteResponse(BaseModel):
    thread_id: str
    final_answer: str
    confidence_summary: dict[str, float]
    citations: list[str]
    loops: int
    halt_reason: str
    trajectory_id: str | None = None
    triage: dict[str, Any]
