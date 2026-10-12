"""Unit tests for Worker Dead Letter Queue (DLQ) and error handling."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.pubsub_publisher import publisher
from src.worker.processor import LifecycleEventProcessor


@pytest.mark.asyncio
async def test_worker_catches_fatal_error_and_routes_to_dlq(db_session: AsyncSession):
    """Verifies that an unhandled downstream error sends the payload to the Dead Letter Queue."""
    processor = LifecycleEventProcessor()
    idempotency_key = "test:dlq:error-key-1"

    # Simulated poison message with force_failure flag
    event_payload = {
        "event_id": "evt-poison-1",
        "event_type": "USER_ONBOARDED",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "correlation_id": "corr-poison-dlq",
        "ticket_id": "TICKET-POISON-01",
        "user_email": "simulate-failure@example.com",
        "full_name": "Poison Message",
        "department": "Engineering",
        "role": "engineer",
        "requested_entitlements": ["cloud:admin"],
        "actor_email": "hr@example.com",
        "context": {"force_failure": True},
        "attempt_count": 1,
    }

    result = await processor.process_event(
        db=db_session,
        event_dict=event_payload,
        idempotency_key=idempotency_key,
    )

    assert result["status"] == "SENT_TO_DLQ"
    assert "error" in result

    # Check DLQ received the event
    dlq_events = publisher.get_dlq_events()
    assert len(dlq_events) == 1
    assert dlq_events[0]["attributes"]["correlation_id"] == "corr-poison-dlq"
    assert "outage" in dlq_events[0]["data"]["error_reason"]
