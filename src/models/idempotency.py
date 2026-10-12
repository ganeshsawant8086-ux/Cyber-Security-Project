"""SQLAlchemy model for Worker Idempotency Tracking."""

from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, String, Text
from src.core.database import Base


class IdempotencyRecord(Base):
    """Enforces exactly-once execution semantics for asynchronous Pub/Sub message handling."""
    __tablename__ = "idempotency_records"

    idempotency_key = Column(String(128), primary_key=True, index=True)
    handler_name = Column(String(64), nullable=False)
    status = Column(String(32), default="PROCESSING", nullable=False)  # PROCESSING, COMPLETED, FAILED
    result_payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
