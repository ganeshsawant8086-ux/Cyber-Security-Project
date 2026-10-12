"""Asynchronous Event Processor for Lifecycle Provisioning and Deprovisioning.

Demonstrates:
- Distributed Idempotency enforcement
- Multi-system downstream orchestration (Directory, Cloud IAM, SaaS)
- Dead Letter Queue (DLQ) routing upon failure
- Safe, structured audit logging without credential exposure
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.mock_cloud import MockCloudAccessAdapter
from src.adapters.mock_directory import MockDirectoryAdapter
from src.adapters.mock_saas import MockSaaSAdapter
from src.core.config import settings
from src.core.logging import get_logger
from src.models.identity import User, UserEntitlement, UserStatus
from src.models.lifecycle_request import LifecycleRequest
from src.schemas.events import PubSubLifecycleEvent
from src.services.audit_service import audit_service
from src.services.pubsub_publisher import publisher
from src.worker.idempotency import IdempotencyGuard

logger = get_logger("worker.processor")


class LifecycleEventProcessor:
    """Processes Pub/Sub lifecycle events and orchestrates downstream provisioning."""

    def __init__(self):
        self.directory_adapter = MockDirectoryAdapter()
        self.cloud_adapter = MockCloudAccessAdapter()
        self.saas_adapter = MockSaaSAdapter()

    async def process_event(
        self,
        db: AsyncSession,
        event_dict: Dict[str, Any],
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Main processing pipeline for a single event."""
        event = PubSubLifecycleEvent(**event_dict)

        logger.info(
            f"Worker processing event {event.event_type} (ticket={event.ticket_id}, user={event.user_email})",
            extra={
                "extra_fields": {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "correlation_id": event.correlation_id,
                }
            },
        )

        # Step 1: Idempotency Check
        can_process, cached_result = await IdempotencyGuard.acquire_or_check(
            db=db,
            idempotency_key=idempotency_key,
            handler_name="LifecycleEventProcessor",
        )

        if not can_process:
            logger.info(f"Duplicate event ignored via idempotency check: {idempotency_key}")
            return cached_result or {"status": "SKIPPED_DUPLICATE"}

        try:
            # Simulated failure scenario for DLQ demonstration
            if "simulate-failure" in event.user_email or event.context.get("force_failure"):
                raise RuntimeError("Simulated target downstream API timeout/outage for DLQ testing")

            results = {}

            if event.event_type == "USER_ONBOARDED":
                results = await self._handle_onboarding(db, event)
            elif event.event_type == "ROLE_UPDATED":
                results = await self._handle_role_update(db, event)
            elif event.event_type == "USER_OFFBOARDED":
                results = await self._handle_offboarding(db, event)
            else:
                logger.warning(f"Unrecognized event type: {event.event_type}")
                results = {"status": "IGNORED", "reason": "Unknown event type"}

            # Mark idempotency completed
            await IdempotencyGuard.mark_completed(db, idempotency_key, results)

            # Update lifecycle request status if exists
            req = await db.scalar(
                select(LifecycleRequest).where(LifecycleRequest.ticket_id == event.ticket_id)
            )
            if req:
                req.status = "PROVISIONED"
                await db.flush()

            # Record Worker Audit Event
            await audit_service.log_event(
                db=db,
                actor="worker-service-account@iam.gserviceaccount.com",
                action=f"WORKER_EXECUTED_{event.event_type}",
                resource_type="user",
                resource_id=event.user_email,
                status="SUCCESS",
                details={"event_id": event.event_id, "results": results},
                correlation_id=event.correlation_id,
            )

            await db.commit()
            return results

        except Exception as exc:
            error_msg = str(exc)
            logger.error(f"Error processing lifecycle event {event.event_id}: {error_msg}")
            await db.rollback()

            # Mark failed in DB
            await IdempotencyGuard.mark_failed(db, idempotency_key, error_msg)

            # Route to Dead-Letter Topic (DLQ)
            dlq_msg_id = await publisher.publish_to_dlq(
                failed_event_payload=event_dict,
                error_reason=error_msg,
                correlation_id=event.correlation_id,
            )

            # Record Audit event for DLQ routing
            await audit_service.log_event(
                db=db,
                actor="worker-service-account@iam.gserviceaccount.com",
                action=f"EVENT_ROUTED_TO_DLQ",
                resource_type="event",
                resource_id=event.event_id,
                status="FAILED",
                details={"error": error_msg, "dlq_message_id": dlq_msg_id},
                correlation_id=event.correlation_id,
            )
            await db.commit()

            return {"status": "SENT_TO_DLQ", "error": error_msg, "dlq_id": dlq_msg_id}

    async def _handle_onboarding(self, db: AsyncSession, event: PubSubLifecycleEvent) -> Dict[str, Any]:
        """Provision user into Directory, Cloud IAM, and SaaS tools."""
        dir_res = await self.directory_adapter.provision_user(
            event.user_email, event.full_name, event.department, event.requested_entitlements
        )
        cloud_res = await self.cloud_adapter.provision_user(
            event.user_email, event.full_name, event.department, event.requested_entitlements
        )
        saas_res = await self.saas_adapter.provision_user(
            event.user_email, event.full_name, event.department, event.requested_entitlements
        )

        # Update database user to ACTIVE
        user = await db.scalar(select(User).where(User.email == event.user_email))
        if user:
            user.status = UserStatus.ACTIVE
            user.updated_at = datetime.now(timezone.utc)

            # Save granted entitlements in DB
            for ent in event.requested_entitlements:
                system_name = ent.split(":")[0] if ":" in ent else "general"
                entitlement_name = ent.split(":")[1] if ":" in ent else ent
                user_ent = UserEntitlement(
                    user_id=user.id,
                    system_name=system_name,
                    entitlement_name=entitlement_name,
                    status="ACTIVE",
                )
                db.add(user_ent)
            await db.flush()

        return {
            "status": "COMPLETED",
            "directory": dir_res,
            "cloud_iam": cloud_res,
            "saas": saas_res,
        }

    async def _handle_role_update(self, db: AsyncSession, event: PubSubLifecycleEvent) -> Dict[str, Any]:
        """Update role and sync entitlements."""
        user = await db.scalar(select(User).where(User.email == event.user_email))
        if user:
            user.role = event.role
            user.updated_at = datetime.now(timezone.utc)
            await db.flush()

        cloud_res = await self.cloud_adapter.update_entitlements(
            event.user_email, event.requested_entitlements, []
        )
        return {"status": "COMPLETED", "cloud_iam": cloud_res}

    async def _handle_offboarding(self, db: AsyncSession, event: PubSubLifecycleEvent) -> Dict[str, Any]:
        """Deprovision user across all downstream systems immediately."""
        dir_res = await self.directory_adapter.deprovision_user(event.user_email)
        cloud_res = await self.cloud_adapter.deprovision_user(event.user_email)
        saas_res = await self.saas_adapter.deprovision_user(event.user_email)

        # Update User in DB to DEPROVISIONED and revoke entitlements
        user = await db.scalar(select(User).where(User.email == event.user_email))
        if user:
            user.status = UserStatus.DEPROVISIONED
            user.updated_at = datetime.now(timezone.utc)

            # Mark entitlements revoked
            entitlements = await db.scalars(
                select(UserEntitlement).where(UserEntitlement.user_id == user.id)
            )
            for ent in entitlements.all():
                ent.status = "REVOKED"
                ent.revoked_at = datetime.now(timezone.utc)
            await db.flush()

        return {
            "status": "COMPLETED",
            "directory": dir_res,
            "cloud_iam": cloud_res,
            "saas": saas_res,
        }


processor = LifecycleEventProcessor()
