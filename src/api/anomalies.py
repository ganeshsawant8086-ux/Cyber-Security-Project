"""Simulated Security Anomalies and Threat Detection endpoints."""

import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.logging import get_logger
from src.core.security import get_current_user
from src.services.audit_service import audit_service
from src.services.policy_client import policy_client

logger = get_logger("anomalies")
anomalies_router = APIRouter(prefix="/api/v1/anomalies", tags=["Simulated Security Anomalies"])


class AnomalySimulationRequest(BaseModel):
    anomaly_type: str = Field(
        ...,
        description="Type of anomaly: IMPOSSIBLE_TRAVEL, UNTRUSTED_DEVICE_ADMIN, PRIVILEGE_ESCALATION, COMPROMISED_CREDENTIAL",
        example="IMPOSSIBLE_TRAVEL",
    )
    target_user_email: str = Field(..., example="alice@example.com")
    simulated_context: Dict[str, Any] = Field(
        default_factory=lambda: {
            "device_trust": "untrusted",
            "risk_level": "critical",
            "origin_geo": "TOR_EXIT_NODE",
        }
    )


class AnomalySimulationResponse(BaseModel):
    anomaly_id: str
    anomaly_type: str
    target_user: str
    policy_action_taken: str
    audit_event_logged: bool
    details: Dict[str, Any]


@anomalies_router.post("/simulate", response_model=AnomalySimulationResponse, status_code=status.HTTP_200_OK)
async def simulate_security_anomaly(
    req: AnomalySimulationRequest,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Simulate a security anomaly to demonstrate context-aware policy mitigation and audit alerting."""
    anomaly_id = f"anom-{uuid.uuid4()}"
    actor = claims.get("email", "secops-test@example.com")

    # Evaluate access under simulated high-risk context
    policy_input = {
        "subject": {"id": req.target_user_email, "roles": ["engineer"], "department": "Engineering"},
        "action": "admin",
        "resource": {"type": "cloud_infra", "sensitivity": "critical", "name": "production-k8s"},
        "context": req.simulated_context,
    }

    eval_result = await policy_client.evaluate_access(policy_input)
    action_taken = "ACCESS_BLOCKED_AND_SESSION_FLAGGED" if not eval_result.get("allow") else "ACCESS_ALLOWED"

    # Log high-severity security audit event
    await audit_service.log_event(
        db=db,
        actor=actor,
        action=f"SECURITY_ANOMALY_DETECTED_{req.anomaly_type}",
        resource_type="identity",
        resource_id=req.target_user_email,
        status="ALERT",
        details={
            "anomaly_id": anomaly_id,
            "anomaly_type": req.anomaly_type,
            "simulated_context": req.simulated_context,
            "policy_result": eval_result,
            "mitigation_action": action_taken,
        },
    )
    await db.commit()

    return AnomalySimulationResponse(
        anomaly_id=anomaly_id,
        anomaly_type=req.anomaly_type,
        target_user=req.target_user_email,
        policy_action_taken=action_taken,
        audit_event_logged=True,
        details={
            "policy_decision": eval_result,
            "security_context": req.simulated_context,
            "mitigation_recommendation": "Session terminated, password reset triggered, MFA challenged.",
        },
    )
