"""Context-Aware Policy Authorization Decisions (OPA Integration)."""

import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user
from src.schemas.policy import PolicyEvaluationRequest, PolicyEvaluationResponse
from src.services.audit_service import audit_service
from src.services.policy_client import policy_client

policy_router = APIRouter(prefix="/api/v1/policies", tags=["Policy Decision Point (OPA)"])


@policy_router.post("/evaluate", response_model=PolicyEvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_access_policy(
    req: PolicyEvaluationRequest,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate context-aware ABAC access authorization via Open Policy Agent (OPA).

    Considers:
    - Subject attributes (role, department)
    - Action (read, write, delete, admin, provision)
    - Resource attributes (sensitivity, type)
    - Contextual signals (device trust posture, risk level)
    """
    decision_id = f"dec-{uuid.uuid4()}"
    client_ip = request.client.host if request.client else "127.0.0.1"

    decision = await policy_client.evaluate_access(req.model_dump())
    allow = decision.get("allow", False)
    reason = decision.get("reason", "Evaluated by OPA")

    # Record decision in structured audit trail
    await audit_service.log_event(
        db=db,
        actor=claims.get("sub", req.subject.email),
        action="EVALUATE_POLICY",
        resource_type=req.resource.type,
        resource_id=req.resource.name,
        status="SUCCESS" if allow else "DENIED",
        details={
            "decision_id": decision_id,
            "allow": allow,
            "reason": reason,
            "subject_roles": req.subject.roles,
            "resource_sensitivity": req.resource.sensitivity,
            "device_trust": req.context.device_trust,
            "risk_level": req.context.risk_level,
        },
        client_ip=client_ip,
    )
    await db.commit()

    return PolicyEvaluationResponse(
        allow=allow,
        reason=reason,
        decision_id=decision_id,
        evaluated_attributes={
            "subject": req.subject.model_dump(),
            "resource": req.resource.model_dump(),
            "context": req.context.model_dump(),
        },
    )
