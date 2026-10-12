"""Pydantic schemas for Audit Logs and Queries."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditFilterQuery(BaseModel):
    """Filter criteria for querying audit trails."""
    actor: Optional[str] = None
    action: Optional[str] = None
    resource_id: Optional[str] = None
    correlation_id: Optional[str] = None
    status: Optional[str] = None
    limit: int = Field(default=50, le=500)


class AuditEventResponse(BaseModel):
    """Structured audit event representation."""
    id: str
    correlation_id: str
    timestamp: datetime
    actor: str
    action: str
    resource_type: str
    resource_id: str
    status: str
    client_ip: Optional[str] = None
    details: Dict[str, Any] = {}
