"""SQLAlchemy models for demo Identity and Entitlements."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from src.core.database import Base


class UserStatus(str):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DEPROVISIONED = "DEPROVISIONED"


class User(Base):
    """Core Identity Record."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_id = Column(String(64), unique=True, index=True, nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    department = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)  # e.g., 'security_engineer', 'devops', 'contractor'
    status = Column(String(32), default=UserStatus.PENDING, index=True, nullable=False)
    risk_score = Column(Integer, default=10, nullable=False)  # 0 to 100 risk rating

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    entitlements = relationship("UserEntitlement", back_populates="user", cascade="all, delete-orphan")


class UserEntitlement(Base):
    """Entitlements and system roles granted across downstream mock targets."""
    __tablename__ = "user_entitlements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    system_name = Column(String(64), nullable=False)  # e.g., 'google_workspace', 'aws_iam', 'slack'
    entitlement_name = Column(String(128), nullable=False)  # e.g., 'SecOps-Admin', 'dev-access'
    status = Column(String(32), default="ACTIVE", nullable=False)  # ACTIVE, REVOKED
    granted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="entitlements")
