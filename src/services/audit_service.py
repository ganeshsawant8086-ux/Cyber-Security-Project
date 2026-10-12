"""Audit logging service for tracking lifecycle changes, authorizations, and anomalies."""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import correlation_id_ctx, get_logger, sanitize_data
from src.models.audit import AuditEvent

logger = get_logger("audit_service")


class AuditService:
    """Records audit logs to the persistent store and structured log streams."""

    @staticmethod
    async def log_event(
        db: AsyncSession,
        actor: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> AuditEvent:
        corr_id = correlation_id or correlation_id_ctx.get() or "system-corr-id"
        sanitized_details = sanitize_data(details or {})

        event = AuditEvent(
            correlation_id=corr_id,
            actor=actor,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            client_ip=client_ip,
            details_json=json.dumps(sanitized_details),
            timestamp=datetime.now(timezone.utc),
        )

        db.add(event)
        await db.flush()

        logger.info(
            f"AUDIT_LOG: actor={actor} action={action} resource={resource_type}:{resource_id} status={status}",
            extra={
                "extra_fields": {
                    "audit_action": action,
                    "status": status,
                    "resource_id": resource_id,
                    "details": sanitized_details,
                }
            },
        )
        return event


audit_service = AuditService()
