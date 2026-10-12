"""Structured Audit Log Lookup Endpoints."""

import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user
from src.models.audit import AuditEvent
from src.schemas.audit import AuditEventResponse

audit_router = APIRouter(prefix="/api/v1/audit", tags=["Audit Trail"])


@audit_router.get("", response_model=List[AuditEventResponse])
async def query_audit_logs(
    actor: Optional[str] = Query(None, description="Filter by actor email"),
    action: Optional[str] = Query(None, description="Filter by action name"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID / target email"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    status: Optional[str] = Query(None, description="Filter by status (SUCCESS, DENIED, FAILED, ALERT)"),
    limit: int = Query(50, ge=1, le=500),
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query structured audit trail with correlation ID tracing and metadata filtering."""
    query = select(AuditEvent).order_by(desc(AuditEvent.timestamp)).limit(limit)

    if actor:
        query = query.where(AuditEvent.actor == actor)
    if action:
        query = query.where(AuditEvent.action == action)
    if resource_id:
        query = query.where(AuditEvent.resource_id == resource_id)
    if correlation_id:
        query = query.where(AuditEvent.correlation_id == correlation_id)
    if status:
        query = query.where(AuditEvent.status == status)

    result = await db.scalars(query)
    events = result.all()

    return [
        AuditEventResponse(
            id=e.id,
            correlation_id=e.correlation_id,
            timestamp=e.timestamp,
            actor=e.actor,
            action=e.action,
            resource_type=e.resource_type,
            resource_id=e.resource_id,
            status=e.status,
            client_ip=e.client_ip,
            details=json.loads(e.details_json) if e.details_json else {},
        )
        for e in events
    ]
