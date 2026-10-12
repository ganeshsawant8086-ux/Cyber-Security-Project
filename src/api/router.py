"""Aggregated API router for version 1 endpoints."""

from fastapi import APIRouter

from src.api.anomalies import anomalies_router
from src.api.auth import auth_router
from src.api.audit import audit_router
from src.api.events import events_router
from src.api.lifecycle import lifecycle_router
from src.api.policies import policy_router
from src.api.reviews import reviews_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(lifecycle_router)
api_v1_router.include_router(policy_router)
api_v1_router.include_router(reviews_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(events_router)
