"""Unit tests for asynchronous worker idempotency and deduplication."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.idempotency import IdempotencyRecord
from src.worker.idempotency import IdempotencyGuard
from src.worker.processor import LifecycleEventProcessor


@pytest.mark.asyncio
async def test_worker_idempotency_prevents_duplicate_execution(db_session: AsyncSession):
    """Verifies that an event with the same idempotency key is processed once and cached thereafter."""
    processor = LifecycleEventProcessor()
    idempotency_key = "test:idempotency:1001"

    event_payload = {
        "event_id": "evt-idemp-1",
        "event_type": "USER_ONBOARDED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": "corr-idemp-1",
        "ticket_id": "TICKET-IDEMP-01",
        "user_email": "idemp.test@example.com",
        "full_name": "Idemp Test",
        "department": "Engineering",
        "role": "engineer",
        "requested_entitlements": ["slack:dev"],
        "actor_email": "hr@example.com",
        "context": {"device_trust": "managed", "risk_level": "low"},
        "attempt_count": 1,
    }

    # First execution: Must process successfully
    first_result = await processor.process_event(
        db=db_session,
        event_dict=event_payload,
        idempotency_key=idempotency_key,
    )
    assert first_result["status"] == "COMPLETED"

    # Second execution: Same idempotency key must be deduplicated
    second_result = await processor.process_event(
        db=db_session,
        event_dict=event_payload,
        idempotency_key=idempotency_key,
    )
    assert second_result == first_result


@pytest.mark.asyncio
async def test_idempotency_guard_failed_retry_allowed(db_session: AsyncSession):
    """Verifies that a message that previously failed is allowed to be retried."""
    key = "test:retry:999"

    # Mark as failed
    can_process, _ = await IdempotencyGuard.acquire_or_check(db_session, key, "TestHandler")
    assert can_process is True
    await IdempotencyGuard.mark_failed(db_session, key, "Downstream temporary timeout")
    await db_session.commit()

    # Retry should be allowed
    can_retry, cached = await IdempotencyGuard.acquire_or_check(db_session, key, "TestHandler")
    assert can_retry is True
    assert cached is None
