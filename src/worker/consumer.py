"""Pub/Sub Consumer supporting both Cloud Run Push endpoints and Pull Subscriber daemon."""

import asyncio
import base64
import json
import os
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import AsyncSessionLocal, get_db
from src.core.logging import correlation_id_ctx, get_logger
from src.worker.processor import processor

logger = get_logger("worker.consumer")

# Push router for Cloud Run / Cloud Functions push subscriptions
worker_router = APIRouter(prefix="/pubsub", tags=["PubSub Worker"])


@worker_router.post("/push")
async def handle_pubsub_push(request: Request, db: AsyncSession = Depends(get_db)):
    """Receives Cloud Run Eventarc / Pub/Sub push subscription messages.

    In production:
    Cloud Run push endpoints are protected by Google Cloud IAM OIDC tokens.
    """
    body = await request.json()
    message = body.get("message")
    if not message or "data" not in message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Pub/Sub push envelope: missing 'message.data'",
        )

    # Decode Pub/Sub base64 payload
    try:
        raw_data = base64.b64decode(message["data"]).decode("utf-8")
        event_dict = json.loads(raw_data)
    except Exception as e:
        logger.error(f"Failed decoding Pub/Sub push message: {str(e)}")
        raise HTTPException(status_code=400, detail="Corrupted message payload")

    message_id = message.get("messageId", "push-msg-unknown")
    correlation_id = message.get("attributes", {}).get("correlation_id", "push-corr-unknown")
    token = correlation_id_ctx.set(correlation_id)

    try:
        result = await processor.process_event(
            db=db,
            event_dict=event_dict,
            idempotency_key=f"pubsub:{message_id}",
        )
        return {"status": "ACK", "result": result}
    finally:
        correlation_id_ctx.reset(token)


async def run_subscriber_daemon():
    """Background polling daemon for local development with Pub/Sub emulator or pull subscription."""
    logger.info("Starting local Pub/Sub subscriber daemon...")

    from google.cloud import pubsub_v1
    from concurrent.futures import TimeoutError

    project_id = settings.GCP_PROJECT_ID
    subscription_id = settings.PUBSUB_SUBSCRIPTION_LIFECYCLE

    try:
        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(project_id, subscription_id)

        def callback(message: pubsub_v1.subscriber.message.Message):
            logger.info(f"Received message {message.message_id} on subscription {subscription_id}")
            try:
                data_str = message.data.decode("utf-8")
                event_dict = json.loads(data_str)
                idempotency_key = f"pubsub:{message.message_id}"

                # Run in new async event loop thread
                async def _proc():
                    async with AsyncSessionLocal() as session:
                        await processor.process_event(session, event_dict, idempotency_key)

                asyncio.run(_proc())
                message.ack()
                logger.info(f"Acknowledged message {message.message_id}")
            except Exception as exc:
                logger.error(f"Error handling message {message.message_id}: {exc}")
                message.nack()

        streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
        logger.info(f"Listening for messages on {subscription_path}...")

        with subscriber:
            try:
                streaming_pull_future.result()
            except TimeoutError:
                streaming_pull_future.cancel()
                streaming_pull_future.result()

    except Exception as e:
        logger.warning(f"Subscriber daemon exited or emulator unavailable: {str(e)}")


if __name__ == "__main__":
    asyncio.run(run_subscriber_daemon())
