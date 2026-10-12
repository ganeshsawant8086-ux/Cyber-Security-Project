"""Service handling identity lifecycle operations: Onboarding, Role Changes, and Offboarding."""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import correlation_id_ctx, get_logger
from src.models.audit import AuditEvent
from src.models.identity import User, UserEntitlement, UserStatus
from src.models.lifecycle_request import LifecycleRequest
from src.schemas.events import PubSubLifecycleEvent
from src.schemas.lifecycle import LifecycleResponse, ServiceNowLifecycleTicket
from src.services.audit_service import audit_service
from src.services.policy_client import policy_client
from src.services.pubsub_publisher import publisher

logger = get_logger("lifecycle_service")


class LifecycleService:
    """Coordinates lifecycle requests, policy decisions, state changes, and event dispatch."""

    async def process_lifecycle_ticket(
        self,
        db: AsyncSession,
        ticket: ServiceNowLifecycleTicket,
        caller_claims: Dict[str, Any],
        client_ip: str = "127.0.0.1",
    ) -> LifecycleResponse:
        corr_id = correlation_id_ctx.get() or f"corr-{uuid.uuid4()}"
        actor_email = caller_claims.get("email", ticket.requester_email)
        caller_roles = caller_claims.get("roles", [])

        logger.info(
            f"Processing lifecycle ticket {ticket.ticket_id} type={ticket.request_type} target={ticket.target_user_email}",
            extra={"extra_fields": {"ticket_id": ticket.ticket_id, "type": ticket.request_type}},
        )

        # Step 1: Idempotency check on ticket_id
        existing_req = await db.scalar(
            select(LifecycleRequest).where(LifecycleRequest.ticket_id == ticket.ticket_id)
        )
        if existing_req:
            logger.info(f"Ticket {ticket.ticket_id} already exists with status {existing_req.status}")
            return LifecycleResponse(
                status=existing_req.status,
                ticket_id=ticket.ticket_id,
                user_email=ticket.target_user_email,
                request_type=ticket.request_type,
                correlation_id=existing_req.correlation_id,
                policy_evaluation={"allow": existing_req.policy_decision == "ALLOW", "reason": existing_req.policy_reason},
                message=f"Ticket previously processed with status {existing_req.status}.",
            )

        # Step 2: Prepare policy evaluation input
        policy_input = {
            "request_type": ticket.request_type,
            "caller_email": actor_email,
            "caller_roles": caller_roles,
            "target_user_email": ticket.target_user_email,
            "target_role": ticket.target_role,
            "context": ticket.context.model_dump(),
        }

        # Step 3: Evaluate authorization and context via OPA
        policy_result = await policy_client.evaluate_lifecycle(policy_input)
        is_allowed = policy_result.get("allow", False)
        reason = policy_result.get("reason", "No reason provided")

        # Step 4: Record LifecycleRequest record in DB
        lifecycle_record = LifecycleRequest(
            ticket_id=ticket.ticket_id,
            request_type=ticket.request_type,
            requester_email=actor_email,
            target_user_email=ticket.target_user_email,
            status="APPROVED" if is_allowed else "REJECTED",
            correlation_id=corr_id,
            policy_decision="ALLOW" if is_allowed else "DENY",
            policy_reason=reason,
            raw_payload=ticket.model_dump_json(),
        )
        db.add(lifecycle_record)

        # Step 5: If Denied, log audit and return
        if not is_allowed:
            await audit_service.log_event(
                db=db,
                actor=actor_email,
                action=f"POLICY_DENIED_{ticket.request_type}",
                resource_type="lifecycle_ticket",
                resource_id=ticket.ticket_id,
                status="DENIED",
                details={"policy_reason": reason, "target_user": ticket.target_user_email},
                client_ip=client_ip,
                correlation_id=corr_id,
            )
            await db.commit()
            return LifecycleResponse(
                status="REJECTED",
                ticket_id=ticket.ticket_id,
                user_email=ticket.target_user_email,
                request_type=ticket.request_type,
                correlation_id=corr_id,
                policy_evaluation=policy_result,
                message=f"Lifecycle request rejected by policy: {reason}",
            )

        # Step 6: Apply Database State Mutation
        user = await db.scalar(
            select(User).where(User.email == ticket.target_user_email)
        )

        if ticket.request_type == "ONBOARD":
            if not user:
                user = User(
                    email=ticket.target_user_email,
                    full_name=ticket.target_user_full_name,
                    department=ticket.department,
                    role=ticket.target_role,
                    status=UserStatus.PENDING,
                )
                db.add(user)
            else:
                user.status = UserStatus.PENDING
                user.role = ticket.target_role
                user.department = ticket.department

        elif ticket.request_type == "ROLE_CHANGE":
            if user:
                user.role = ticket.target_role
                user.updated_at = datetime.now(timezone.utc)

        elif ticket.request_type == "OFFBOARD":
            if user:
                user.status = UserStatus.DEPROVISIONED
                user.updated_at = datetime.now(timezone.utc)

        await db.flush()

        # Step 7: Publish Asynchronous Event to Pub/Sub
        event = PubSubLifecycleEvent(
            event_id=f"evt-{uuid.uuid4()}",
            event_type=f"USER_{ticket.request_type}ED" if ticket.request_type != "ROLE_CHANGE" else "ROLE_UPDATED",
            timestamp=datetime.now(timezone.utc),
            correlation_id=corr_id,
            ticket_id=ticket.ticket_id,
            user_email=ticket.target_user_email,
            full_name=ticket.target_user_full_name,
            department=ticket.department,
            role=ticket.target_role,
            requested_entitlements=ticket.requested_entitlements,
            actor_email=actor_email,
            context=ticket.context.model_dump(),
        )

        await publisher.publish_lifecycle_event(event)

        # Step 8: Record Audit Event
        await audit_service.log_event(
            db=db,
            actor=actor_email,
            action=f"LIFECYCLE_{ticket.request_type}_APPROVED",
            resource_type="user",
            resource_id=ticket.target_user_email,
            status="SUCCESS",
            details={
                "ticket_id": ticket.ticket_id,
                "role": ticket.target_role,
                "entitlements": ticket.requested_entitlements,
            },
            client_ip=client_ip,
            correlation_id=corr_id,
        )

        await db.commit()

        return LifecycleResponse(
            status="ACCEPTED",
            ticket_id=ticket.ticket_id,
            user_email=ticket.target_user_email,
            request_type=ticket.request_type,
            correlation_id=corr_id,
            policy_evaluation=policy_result,
            message="Lifecycle request approved by policy and dispatched to orchestration worker.",
        )


lifecycle_service = LifecycleService()
