"""Event Processing Status and Dead-Letter Inspection Endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.idempotency import IdempotencyRecord
from src.models.lifecycle_request import LifecycleRequest
from src.schemas.events import EventProcessingStatus
from src.services.pubsub_publisher import publisher

events_router = APIRouter(prefix="/api/v1/events", tags=["Event Processing & DLQ"])


@events_router.get("/status/{ticket_id}", response_model=EventProcessingStatus)
async def get_event_status_by_ticket(
    ticket_id: str,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Inspect async lifecycle event processing and provision status."""
    req = await db.scalar(select(LifecycleRequest).where(LifecycleRequest.ticket_id == ticket_id))
    if not req:
        raise HTTPException(status_code=404, detail=f"No lifecycle record found for ticket {ticket_id}")

    return EventProcessingStatus(
        event_id=f"evt-{req.ticket_id}",
        ticket_id=req.ticket_id,
        status=req.status,
        correlation_id=req.correlation_id,
        details=f"Policy decision: {req.policy_decision}. Reason: {req.policy_reason}",
    )


@events_router.get("/dlq", response_model=List[Dict[str, Any]])
async def inspect_dead_letter_queue(claims: Dict[str, Any] = Depends(get_current_user)):
    """Inspect dead-letter queue messages for troubleshooting failed async events."""
    return publisher.get_dlq_events()


@events_router.get("/published", response_model=List[Dict[str, Any]])
async def inspect_published_events(claims: Dict[str, Any] = Depends(get_current_user)):
    """Inspect published in-flight messages (for testing and verification)."""
    return publisher.get_published_events()
