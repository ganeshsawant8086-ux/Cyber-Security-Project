"""Google Cloud Pub/Sub Event Publisher with Emulator and In-Memory fallback support.

Demonstrates:
- Asynchronous messaging with correlation ID metadata injection
- Cloud Run / Cloud Functions event decoupling
- Local Pub/Sub emulator support (PUBSUB_EMULATOR_HOST)
- Fallback in-memory queue for offline unit testing
"""

import json
import os
from typing import Any, Dict, List, Optional
from google.cloud import pubsub_v1
from src.core.config import settings
from src.core.logging import correlation_id_ctx, get_logger, sanitize_data
from src.schemas.events import PubSubLifecycleEvent

logger = get_logger("pubsub_publisher")


class PubSubPublisher:
    """Manages publishing lifecycle events to GCP Pub/Sub."""

    def __init__(self):
        self.project_id = settings.GCP_PROJECT_ID
        self.topic_name = settings.PUBSUB_TOPIC_LIFECYCLE
        self.dlq_topic_name = settings.PUBSUB_TOPIC_DLQ
        self._in_memory_events: List[Dict[str, Any]] = []
        self._dlq_events: List[Dict[str, Any]] = []

        # Determine if Pub/Sub client can be initialized
        self._client: Optional[pubsub_v1.PublisherClient] = None
        self._use_emulator_or_cloud = False

        if settings.PUBSUB_EMULATOR_HOST or os.getenv("PUBSUB_EMULATOR_HOST"):
            # Running with local emulator
            try:
                self._client = pubsub_v1.PublisherClient()
                self._use_emulator_or_cloud = True
                logger.info(f"Initialized Pub/Sub Publisher connected to emulator: {settings.PUBSUB_EMULATOR_HOST}")
            except Exception as e:
                logger.warning(f"Failed initializing Pub/Sub emulator client ({str(e)}). Using in-memory queue.")
        else:
            logger.info("PUBSUB_EMULATOR_HOST not set; using local in-memory event publisher for tests.")

    def get_topic_path(self, topic: str) -> str:
        return f"projects/{self.project_id}/topics/{topic}"

    async def publish_lifecycle_event(self, event: PubSubLifecycleEvent) -> str:
        """Publish a user lifecycle event to Pub/Sub with correlation ID attributes."""
        corr_id = correlation_id_ctx.get() or event.correlation_id

        # Convert event to dict and sanitize
        payload = sanitize_data(event.model_dump(mode="json"))
        data_bytes = json.dumps(payload).encode("utf-8")

        attributes = {
            "event_type": event.event_type,
            "correlation_id": corr_id,
            "ticket_id": event.ticket_id,
            "user_email": event.user_email,
        }

        if self._use_emulator_or_cloud and self._client:
            try:
                topic_path = self.get_topic_path(self.topic_name)
                future = self._client.publish(topic_path, data=data_bytes, **attributes)
                message_id = future.result(timeout=5.0)
                logger.info(
                    f"Published lifecycle event {event.event_type} to Pub/Sub (msg_id={message_id})",
                    extra={"extra_fields": {"ticket_id": event.ticket_id, "user_email": event.user_email}},
                )
                return str(message_id)
            except Exception as e:
                logger.error(f"Error publishing to Pub/Sub: {str(e)}. Recording to in-memory queue.")

        # Fallback in-memory
        msg_id = f"mock-msg-{len(self._in_memory_events) + 1}"
        self._in_memory_events.append({"id": msg_id, "data": payload, "attributes": attributes})
        logger.info(
            f"[MOCK PUBSUB] Published {event.event_type} event to in-memory queue (id={msg_id})"
        )
        return msg_id

    async def publish_to_dlq(self, failed_event_payload: Dict[str, Any], error_reason: str, correlation_id: str) -> str:
        """Publish a unprocessable/dead-letter message to the Dead Letter Queue topic."""
        sanitized_payload = sanitize_data(failed_event_payload)
        dlq_envelope = {
            "original_payload": sanitized_payload,
            "error_reason": error_reason,
            "correlation_id": correlation_id,
        }
        data_bytes = json.dumps(dlq_envelope).encode("utf-8")
        attributes = {"status": "DEAD_LETTER", "correlation_id": correlation_id}

        if self._use_emulator_or_cloud and self._client:
            try:
                topic_path = self.get_topic_path(self.dlq_topic_name)
                future = self._client.publish(topic_path, data=data_bytes, **attributes)
                msg_id = future.result(timeout=5.0)
                logger.warning(f"Sent failed message to DLQ {topic_path} (msg_id={msg_id})")
                return str(msg_id)
            except Exception as e:
                logger.error(f"Failed to publish to DLQ Pub/Sub: {str(e)}")

        msg_id = f"mock-dlq-{len(self._dlq_events) + 1}"
        self._dlq_events.append({"id": msg_id, "data": dlq_envelope, "attributes": attributes})
        logger.warning(f"[MOCK PUBSUB] Sent failed message to in-memory DLQ (id={msg_id})")
        return msg_id

    def get_published_events(self) -> List[Dict[str, Any]]:
        """Utility for inspection in tests and demo runs."""
        return list(self._in_memory_events)

    def get_dlq_events(self) -> List[Dict[str, Any]]:
        """Utility for inspection in tests and demo runs."""
        return list(self._dlq_events)

    def clear(self):
        """Reset mock queues."""
        self._in_memory_events.clear()
        self._dlq_events.clear()


publisher = PubSubPublisher()
