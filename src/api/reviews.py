"""Access Review campaigns and entitlement attestation endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import get_db
from src.core.security import get_current_user, require_role
from src.models.identity import User, UserEntitlement
from src.models.review import AccessReviewCampaign, AccessReviewItem
from src.schemas.reviews import (
    AccessReviewCampaignCreate,
    AccessReviewCampaignResponse,
    AccessReviewDecisionRequest,
    AccessReviewItemResponse,
)
from src.services.audit_service import audit_service

reviews_router = APIRouter(prefix="/api/v1/reviews", tags=["Access Reviews & Attestation"])


@reviews_router.post("/campaigns", response_model=AccessReviewCampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_access_review_campaign(
    req: AccessReviewCampaignCreate,
    claims: Dict[str, Any] = Depends(require_role("identity_admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a periodic access review campaign for all active user entitlements."""
    now = datetime.now(timezone.utc)
    due_date = now + timedelta(days=req.due_days)

    campaign = AccessReviewCampaign(
        campaign_name=req.campaign_name,
        created_by=claims.get("email", "admin@example.com"),
        due_date=due_date,
    )
    db.add(campaign)
    await db.flush()

    # Collect all active entitlements
    query = select(UserEntitlement).where(UserEntitlement.status == "ACTIVE")
    result = await db.scalars(query)
    active_entitlements = result.all()

    items: List[AccessReviewItem] = []
    for ent in active_entitlements:
        user = await db.scalar(select(User).where(User.id == ent.user_id))
        user_email = user.email if user else "unknown@example.com"
        item = AccessReviewItem(
            campaign_id=campaign.id,
            user_email=user_email,
            system_name=ent.system_name,
            entitlement_name=ent.entitlement_name,
            decision="PENDING",
        )
        db.add(item)
        items.append(item)

    await db.commit()

    return AccessReviewCampaignResponse(
        id=campaign.id,
        campaign_name=campaign.campaign_name,
        status=campaign.status,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        due_date=campaign.due_date,
        items=[
            AccessReviewItemResponse(
                id=i.id,
                campaign_id=i.campaign_id,
                user_email=i.user_email,
                system_name=i.system_name,
                entitlement_name=i.entitlement_name,
                decision=i.decision,
            )
            for i in items
        ],
    )


@reviews_router.get("/campaigns", response_model=List[AccessReviewCampaignResponse])
async def list_campaigns(
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all access review campaigns with items."""
    stmt = select(AccessReviewCampaign).options(selectinload(AccessReviewCampaign.items))
    result = await db.scalars(stmt)
    campaigns = result.all()

    return [
        AccessReviewCampaignResponse(
            id=c.id,
            campaign_name=c.campaign_name,
            status=c.status,
            created_by=c.created_by,
            created_at=c.created_at,
            due_date=c.due_date,
            items=[
                AccessReviewItemResponse(
                    id=i.id,
                    campaign_id=i.campaign_id,
                    user_email=i.user_email,
                    system_name=i.system_name,
                    entitlement_name=i.entitlement_name,
                    decision=i.decision,
                    reviewer_email=i.reviewer_email,
                    justification=i.justification,
                    decided_at=i.decided_at,
                )
                for i in c.items
            ],
        )
        for c in campaigns
    ]


@reviews_router.post("/items/{item_id}/decide", response_model=AccessReviewItemResponse)
async def submit_review_decision(
    item_id: str,
    decision_req: AccessReviewDecisionRequest,
    claims: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit certification or revocation decision for a specific entitlement."""
    item = await db.scalar(select(AccessReviewItem).where(AccessReviewItem.id == item_id))
    if not item:
        raise HTTPException(status_code=404, detail="Review item not found")

    reviewer = claims.get("email", "reviewer@example.com")
    item.decision = decision_req.decision
    item.reviewer_email = reviewer
    item.justification = decision_req.justification
    item.decided_at = datetime.now(timezone.utc)

    # If revoked, update entitlement status in database
    if decision_req.decision == "REVOKED":
        user = await db.scalar(select(User).where(User.email == item.user_email))
        if user:
            ent = await db.scalar(
                select(UserEntitlement).where(
                    UserEntitlement.user_id == user.id,
                    UserEntitlement.system_name == item.system_name,
                    UserEntitlement.entitlement_name == item.entitlement_name,
                )
            )
            if ent:
                ent.status = "REVOKED"
                ent.revoked_at = datetime.now(timezone.utc)

    await audit_service.log_event(
        db=db,
        actor=reviewer,
        action=f"ACCESS_REVIEW_{decision_req.decision}",
        resource_type="entitlement",
        resource_id=f"{item.user_email}:{item.entitlement_name}",
        status="SUCCESS",
        details={"justification": decision_req.justification},
    )

    await db.commit()

    return AccessReviewItemResponse(
        id=item.id,
        campaign_id=item.campaign_id,
        user_email=item.user_email,
        system_name=item.system_name,
        entitlement_name=item.entitlement_name,
        decision=item.decision,
        reviewer_email=item.reviewer_email,
        justification=item.justification,
        decided_at=item.decided_at,
    )
