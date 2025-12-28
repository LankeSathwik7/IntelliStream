"""Chat endpoints with agent workflow integration."""

import json
import logging
import traceback
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, field_validator

from app.agents.graph import run_agent_workflow, stream_agent_workflow
from app.services.pdf_generator import pdf_generator
from app.services.rate_limiter import chat_limiter
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


class HistoryMessage(BaseModel):
    """A message in conversation history."""
    role: str
    content: str


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str
    thread_id: Optional[str] = None
    sources: List[str] = ["news", "research"]
    history: Optional[List[HistoryMessage]] = None  # Conversation history

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """Validate message is not empty."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 10000:
            raise ValueError("Message too long (max 10000 characters)")
        return v.strip()


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str
    thread_id: str
    sources: List[dict] = []
    agent_trace: List[dict] = []
    latency_ms: int = 0


async def check_rate_limit(request: Request) -> str:
    """Check rate limit and return identifier."""
    # Use IP address as identifier for anonymous users
    client_ip = request.client.host if request.client else "unknown"
    identifier = client_ip

    allowed, info = await chat_limiter.check_rate_limit(identifier, "chat")
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {info.get('retry_after', 60)} seconds.",
            headers={"Retry-After": str(info.get("retry_after", 60))}
        )
    return identifier


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, req: Request):
    """Non-streaming chat endpoint."""
    await check_rate_limit(req)
    thread_id = request.thread_id or str(uuid.uuid4())

    try:
        result = await run_agent_workflow(
            query=request.message,
            thread_id=thread_id,
        )

        return ChatResponse(
            response=result["response"],
            thread_id=result["thread_id"],
            sources=result["sources"],
            agent_trace=result["agent_trace"],
            latency_ms=result["latency_ms"],
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """SSE streaming chat endpoint."""
    await check_rate_limit(req)
    thread_id = request.thread_id or str(uuid.uuid4())

    # Convert history to dict format
    history = None
    if request.history:
        history = [{"role": h.role, "content": h.content} for h in request.history]

    async def event_generator():
        try:
            async for event in stream_agent_workflow(
                query=request.message,
                thread_id=thread_id,
                history=history,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class ExportRequest(BaseModel):
    """PDF export request model."""

    messages: List[dict]
    title: Optional[str] = "IntelliStream Report"
    include_sources: bool = True


@router.post("/export/pdf")
async def export_pdf(request: ExportRequest):
    """
    Export conversation to PDF.

    Args:
        request: Export request with messages and options

    Returns:
        PDF file download
    """
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages to export")

        pdf_bytes = await pdf_generator.generate_conversation_report(
            messages=request.messages,
            title=request.title,
            include_sources=request.include_sources,
        )

        # Determine content type based on output
        is_html = pdf_bytes.startswith(b"<!DOCTYPE")
        content_type = "text/html" if is_html else "application/pdf"
        file_ext = "html" if is_html else "pdf"

        return Response(
            content=pdf_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="intellistream-report.{file_ext}"'
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
