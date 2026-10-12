"""ServiceNow-style Ingress Endpoints for Identity Lifecycle Orchestration."""

from typing import Any, Dict
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.security import get_current_user
from src.schemas.lifecycle import LifecycleResponse, ServiceNowLifecycleTicket
from src.services.lifecycle_service import lifecycle_service

lifecycle_router = APIRouter(prefix="/api/v1/lifecycle", tags=["Identity Lifecycle Orchestration"])


@lifecycle_router.post("/request", response_model=LifecycleResponse, status_code=status.HTTP_200_OK)
async def process_servicenow_request(
    ticket: ServiceNowLifecycleTicket,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Receive and evaluate a ServiceNow lifecycle ticket (ONBOARD, ROLE_CHANGE, OFFBOARD).

    Steps executed:
    1. Caller authentication via JWT Bearer token
    2. Context-aware ABAC policy check via Open Policy Agent (OPA)
    3. Identity record state updates in PostgreSQL
    4. Lifecycle event publishing to Google Cloud Pub/Sub
    5. Structured audit event generation
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    response = await lifecycle_service.process_lifecycle_ticket(
        db=db,
        ticket=ticket,
        caller_claims=claims,
        client_ip=client_ip,
    )
    return response


@lifecycle_router.post("/onboard", response_model=LifecycleResponse, status_code=status.HTTP_200_OK)
async def onboard_user(
    ticket: ServiceNowLifecycleTicket,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated endpoint to onboard a new employee."""
    ticket.request_type = "ONBOARD"
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await lifecycle_service.process_lifecycle_ticket(
        db=db, ticket=ticket, caller_claims=claims, client_ip=client_ip
    )


@lifecycle_router.post("/offboard", response_model=LifecycleResponse, status_code=status.HTTP_200_OK)
async def offboard_user(
    ticket: ServiceNowLifecycleTicket,
    request: Request,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dedicated endpoint to immediately offboard a user and revoke all credentials."""
    ticket.request_type = "OFFBOARD"
    client_ip = request.client.host if request.client else "127.0.0.1"
    return await lifecycle_service.process_lifecycle_ticket(
        db=db, ticket=ticket, caller_claims=claims, client_ip=client_ip
    )
