"""SQLAlchemy model for Lifecycle Ingestion Requests (ServiceNow Tickets)."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, String, Text
from src.core.database import Base


class LifecycleRequest(Base):
    """Tracks ingress requests from ITSM systems (ServiceNow mock)."""
    __tablename__ = "lifecycle_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticket_id = Column(String(64), unique=True, index=True, nullable=False)
    request_type = Column(String(32), nullable=False)  # ONBOARD, ROLE_CHANGE, OFFBOARD
    requester_email = Column(String(255), nullable=False)
    target_user_email = Column(String(255), nullable=False)
    status = Column(String(32), default="PENDING", nullable=False)  # PENDING, APPROVED, REJECTED, PROVISIONED, FAILED
    correlation_id = Column(String(64), index=True, nullable=False)
    policy_decision = Column(String(32), nullable=True)  # ALLOW, DENY
    policy_reason = Column(String(255), nullable=True)
    raw_payload = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
