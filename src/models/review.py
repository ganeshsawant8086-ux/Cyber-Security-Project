"""SQLAlchemy model for Access Review campaigns and certifications."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from src.core.database import Base


class AccessReviewCampaign(Base):
    """Tracks periodic access reviews/certifications (e.g., SOX/SOC2 compliance reviews)."""
    __tablename__ = "access_review_campaigns"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_name = Column(String(255), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, COMPLETED, CANCELLED
    created_by = Column(String(255), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    items = relationship("AccessReviewItem", back_populates="campaign", cascade="all, delete-orphan")


class AccessReviewItem(Base):
    """Specific user-role review decision item within a campaign."""
    __tablename__ = "access_review_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String(36), ForeignKey("access_review_campaigns.id", ondelete="CASCADE"), nullable=False)
    user_email = Column(String(255), nullable=False)
    system_name = Column(String(64), nullable=False)
    entitlement_name = Column(String(128), nullable=False)
    decision = Column(String(32), default="PENDING", nullable=False)  # PENDING, CERTIFIED, REVOKED
    reviewer_email = Column(String(255), nullable=True)
    justification = Column(String(255), nullable=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    campaign = relationship("AccessReviewCampaign", back_populates="items")
