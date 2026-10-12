"""Pydantic schemas for ServiceNow-style Lifecycle Webhook requests."""

from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class ContextAttributes(BaseModel):
    """Context-aware request attributes evaluated by Open Policy Agent."""
    device_trust: str = Field(
        default="managed",
        description="Device posture: 'managed', 'untrusted', 'compliant'",
        example="managed"
    )
    risk_level: str = Field(
        default="low",
        description="Calculated risk score level: 'low', 'medium', 'high', 'critical'",
        example="low"
    )
    ip_address: Optional[str] = Field(default="192.168.1.100", example="192.168.1.100")
    geo_location: Optional[str] = Field(default="US-WEST", example="US-WEST")


class ServiceNowLifecycleTicket(BaseModel):
    """Mock ServiceNow change/request ticket envelope."""
    ticket_id: str = Field(..., description="ITSM Ticket Reference", example="REQ0098124")
    request_type: str = Field(..., description="Type of request: ONBOARD, ROLE_CHANGE, OFFBOARD", example="ONBOARD")
    requester_email: EmailStr = Field(..., example="hr_admin@example.com")
    target_user_email: EmailStr = Field(..., example="alice@example.com")
    target_user_full_name: str = Field(..., example="Alice Engineer")
    department: str = Field(..., example="Cloud Infrastructure")
    target_role: str = Field(..., example="security_engineer")
    justification: str = Field(..., example="New hire onboarding into Cloud Security team")
    requested_entitlements: List[str] = Field(
        default_factory=list,
        example=["aws_sso:SecOps-Admin", "google_workspace:security-team", "slack:secops"]
    )
    context: ContextAttributes = Field(default_factory=ContextAttributes)


class LifecycleResponse(BaseModel):
    """Lifecycle operation outcome response."""
    status: str  # ACCEPTED, PROVISIONED, REJECTED, SUSPENDED, DEPROVISIONED
    ticket_id: str
    user_email: str
    request_type: str
    correlation_id: str
    policy_evaluation: dict
    message: str
