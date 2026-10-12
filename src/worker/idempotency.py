"""Worker Idempotency Guard to prevent duplicate processing on Pub/Sub redelivery."""

from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.idempotency import IdempotencyRecord

logger = get_logger("worker.idempotency")


class IdempotencyGuard:
    """Manages idempotency states in PostgreSQL / database."""

    @staticmethod
    async def acquire_or_check(
        db: AsyncSession,
        idempotency_key: str,
        handler_name: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if message has already been processed or is currently in-flight.

        Returns:
            Tuple[is_new_or_retryable, cached_result_dict]
        """
        record = await db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
        )

        if record:
            if record.status == "COMPLETED":
                logger.info(f"Idempotent message hit: key={idempotency_key} was already COMPLETED. Skipping.")
                result = json.loads(record.result_payload) if record.result_payload else {}
                return False, result
            elif record.status == "PROCESSING":
                logger.warning(f"Message key={idempotency_key} is currently PROCESSING by another worker instance.")
                return False, None
            # If FAILED, allow retry
            logger.info(f"Retrying previously FAILED message: key={idempotency_key}")
            record.status = "PROCESSING"
            await db.flush()
            return True, None

        # Create new in-flight record
        new_record = IdempotencyRecord(
            idempotency_key=idempotency_key,
            handler_name=handler_name,
            status="PROCESSING",
        )
        db.add(new_record)
        await db.flush()
        return True, None

    @staticmethod
    async def mark_completed(
        db: AsyncSession,
        idempotency_key: str,
        result: Dict[str, Any],
    ) -> None:
        """Mark idempotency record as successfully completed."""
        record = await db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
        )
        if record:
            record.status = "COMPLETED"
            record.result_payload = json.dumps(result)
            record.completed_at = datetime.now(timezone.utc)
            await db.flush()

    @staticmethod
    async def mark_failed(
        db: AsyncSession,
        idempotency_key: str,
        error_message: str,
    ) -> None:
        """Mark record as failed so retry or DLQ can inspect."""
        record = await db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.idempotency_key == idempotency_key)
        )
        if record:
            record.status = "FAILED"
            record.result_payload = json.dumps({"error": error_message})
            await db.flush()
