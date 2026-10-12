"""Pydantic schemas for Access Reviews and Certification Campaigns."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field


class AccessReviewCampaignCreate(BaseModel):
    """Payload to initiate a new periodic access review."""
    campaign_name: str = Field(..., example="Q4 2026 SOC2 Cloud Admin Attestation")
    due_days: int = Field(default=14, ge=1, le=90)


class AccessReviewItemResponse(BaseModel):
    id: str
    campaign_id: str
    user_email: str
    system_name: str
    entitlement_name: str
    decision: str  # PENDING, CERTIFIED, REVOKED
    reviewer_email: Optional[str] = None
    justification: Optional[str] = None
    decided_at: Optional[datetime] = None


class AccessReviewCampaignResponse(BaseModel):
    id: str
    campaign_name: str
    status: str
    created_by: str
    created_at: datetime
    due_date: Optional[datetime] = None
    items: List[AccessReviewItemResponse] = []


class AccessReviewDecisionRequest(BaseModel):
    decision: str = Field(..., description="CERTIFIED or REVOKED", example="CERTIFIED")
    justification: str = Field(..., example="Verified active member of DevOps team")
