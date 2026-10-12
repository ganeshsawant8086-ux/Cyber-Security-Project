"""Pydantic schemas for Policy Evaluation (OPA ABAC/RBAC decisions)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.schemas.lifecycle import ContextAttributes


class PolicySubject(BaseModel):
    """Subject/Actor requesting access."""
    id: str = Field(..., example="usr-alice-101")
    email: str = Field(..., example="alice@example.com")
    roles: List[str] = Field(..., example=["security_engineer"])
    department: str = Field(default="Engineering", example="Engineering")


class PolicyResource(BaseModel):
    """Resource being accessed."""
    type: str = Field(..., example="cloud_infra")
    name: str = Field(..., example="gcp-production-kms")
    sensitivity: str = Field(default="high", example="high")  # low, medium, high, critical


class PolicyEvaluationRequest(BaseModel):
    """Payload sent to OPA or local PEP for an authorization decision."""
    subject: PolicySubject
    action: str = Field(..., example="read", description="Action being performed: read, write, delete, provision, admin")
    resource: PolicyResource
    context: ContextAttributes = Field(default_factory=ContextAttributes)


class PolicyEvaluationResponse(BaseModel):
    """Decision output from OPA policy."""
    allow: bool
    reason: str
    decision_id: Optional[str] = None
    evaluated_attributes: Dict[str, Any]
