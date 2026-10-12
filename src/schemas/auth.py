"""Pydantic schemas for Authentication and Token Management."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class TokenRequest(BaseModel):
    """Demo endpoint payload to generate a signed JWT bearer token."""
    subject: str = Field(..., description="Subject identity (e.g. employee ID or user email)", example="usr-alice-101")
    email: EmailStr = Field(..., description="Actor email", example="alice@example.com")
    roles: List[str] = Field(default=["engineer"], description="Assigned roles", example=["engineer", "cloud_admin"])
    department: str = Field(default="Engineering", example="Engineering")
    additional_claims: Optional[Dict[str, Any]] = Field(default=None, description="Optional extra OIDC claims")
    expires_in_minutes: Optional[int] = Field(default=60, description="Token validity window in minutes")


class TokenResponse(BaseModel):
    """Bearer token response payload."""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    issuer: str
    audience: str
    scope: str = "identity:lifecycle"


class TokenValidateRequest(BaseModel):
    """Token inspection payload."""
    token: str = Field(..., description="Raw JWT string to inspect")


class SessionInspectResponse(BaseModel):
    """Token claims inspection and verification status response."""
    valid: bool
    subject: str
    email: Optional[str] = None
    roles: List[str] = []
    issuer: str
    audience: str
    issued_at: int
    expires_at: int
    remaining_seconds: int
    all_claims: Dict[str, Any]
