"""FastAPI Middlewares: Correlation ID tracking, Security Headers, and Rate Limiting guidance."""

import time
import uuid
from collections import defaultdict
from typing import Callable, Dict, List
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.core.logging import correlation_id_ctx, get_logger

logger = get_logger("middleware")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Propagates X-Correlation-ID across all requests, logs, and outbound events."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = f"corr-{uuid.uuid4()}"

        # Set into context variable for logger
        token = correlation_id_ctx.set(corr_id)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = corr_id
            return response
        finally:
            correlation_id_ctx.reset(token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforces OWASP recommended HTTP response security headers."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy:
        # Allows self-hosted assets and Swagger UI CDN dependencies (jsdelivr, google fonts, cdnjs)
        # while preventing framing and clickjacking attacks.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://fastapi.tiangolo.com "
            "https://fonts.googleapis.com https://fonts.gstatic.com "
            "https://cdnjs.cloudflare.com data:; "
            "frame-ancestors 'none'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory rate limiter demonstrating DDoS / brute-force protection concepts.

    In production:
    Replace with Google Cloud Armor on Cloud Load Balancer or Redis-backed distributed token bucket.
    """

    def __init__(self, app, max_requests_per_minute: int = 120):
        super().__init__(app)
        self.max_requests = max_requests_per_minute
        self.request_records: Dict[str, List[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Exempt health check endpoints
        if request.url.path in ["/healthz", "/readyz"]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - 60.0

        # Prune old timestamps
        records = [t for t in self.request_records[client_ip] if t > window_start]
        self.request_records[client_ip] = records

        if len(records) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please retry in 60 seconds.",
                },
                headers={"Retry-After": "60"},
            )

        self.request_records[client_ip].append(now)
        return await call_next(request)
