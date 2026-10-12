"""Pydantic schemas for Pub/Sub Lifecycle Events and processing status."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PubSubLifecycleEvent(BaseModel):
    """Schema for asynchronous events published to Google Cloud Pub/Sub."""
    event_id: str
    event_type: str  # USER_ONBOARDED, ROLE_UPDATED, USER_OFFBOARDED, ANOMALY_TRIGGERED
    timestamp: datetime
    correlation_id: str
    ticket_id: str
    user_email: str
    full_name: str
    department: str
    role: str
    requested_entitlements: List[str] = []
    actor_email: str
    context: Dict[str, Any] = {}
    attempt_count: int = 1


class EventProcessingStatus(BaseModel):
    """Response representing async processing state."""
    event_id: str
    ticket_id: str
    status: str  # QUEUED, PROCESSING, COMPLETED, FAILED, SENT_TO_DLQ
    correlation_id: str
    details: Optional[str] = None
