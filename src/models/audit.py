"""SQLAlchemy model for Structured Audit Events."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, String, Text
from src.core.database import Base


class AuditEvent(Base):
    """Immutable audit trail of access requests, policy decisions, and provisioning actions."""
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    correlation_id = Column(String(64), index=True, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    actor = Column(String(255), nullable=False)  # User email or system service account
    action = Column(String(64), nullable=False)  # e.g., 'ONBOARD_USER', 'EVALUATE_POLICY', 'REVOKE_ENTITLEMENT'
    resource_type = Column(String(64), nullable=False)  # e.g., 'user', 'role', 'session'
    resource_id = Column(String(255), nullable=False)  # Target email or resource identifier
    status = Column(String(32), nullable=False)  # SUCCESS, DENIED, FAILED, RETRIED
    client_ip = Column(String(64), nullable=True)
    details_json = Column(Text, nullable=True)  # Structured, sanitized JSON metadata
