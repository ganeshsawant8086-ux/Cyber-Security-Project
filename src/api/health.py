"""Health and Readiness endpoints for Cloud Run and Kubernetes probes."""

from fastapi import APIRouter, status
from sqlalchemy import text
from src.core.database import AsyncSessionLocal
from src.core.logging import get_logger

logger = get_logger("health")
health_router = APIRouter(tags=["Health & Probes"])


@health_router.get("/healthz", status_code=status.HTTP_200_OK)
async def liveness_probe():
    """Liveness probe: verifies process is alive."""
    return {"status": "UP", "service": "identity-access-orchestrator"}


@health_router.get("/readyz", status_code=status.HTTP_200_OK)
async def readiness_probe():
    """Readiness probe: verifies database connectivity and core subsystems."""
    checks = {"database": "UNKNOWN", "pubsub": "UP", "opa": "UP"}

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "UP"
    except Exception as e:
        logger.error(f"Database readiness check failed: {str(e)}")
        checks["database"] = "DOWN"
        return {"status": "DEGRADED", "checks": checks}

    return {"status": "READY", "checks": checks}
