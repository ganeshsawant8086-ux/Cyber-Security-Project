"""FastAPI Application Entrypoint for Identity Lifecycle & Access Orchestration.

DEMO DISCLAIMER:
This project is an architectural demonstration of modern cloud security patterns:
- OIDC/OAuth2 authentication (with local mock keys for isolated testing)
- ABAC authorization policies using Open Policy Agent (OPA)
- Event-driven identity lifecycle via Google Cloud Pub/Sub
- Immutable structured audit logging and threat detection simulation

NOT PRODUCTION READY: Real production deployment requires external OIDC IdP integration,
GCP Secret Manager/KMS, Cloud Armor DDoS mitigation, and production SCIM/API targets.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.health import health_router
from src.api.router import api_v1_router
from src.core.config import settings
from src.core.database import init_db
from src.core.logging import get_logger
from src.core.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
)
from src.core.security import SecurityException
from src.worker.consumer import worker_router

logger = get_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan lifecycle manager (startup/shutdown tasks)."""
    logger.info("Starting Identity Lifecycle & Access Orchestration service...")
    await init_db()
    yield
    logger.info("Shutting down Identity Lifecycle & Access Orchestration service...")


app = FastAPI(
    title="Identity Lifecycle & Access Orchestration Platform",
    description="""
## Cloud Security Architecture Portfolio Demo

Demonstrates an end-to-end access management pipeline:
* **ServiceNow Mock Ingress:** Receives change/lifecycle requests (Onboarding, Role Changes, Offboarding).
* **OIDC/OAuth2 Authentication:** Validates caller identity tokens with standard claim checks (exp, iss, aud, roles).
* **Policy Decision Point (PDP):** Context-aware Attribute-Based Access Control (ABAC) via Open Policy Agent (OPA).
* **Asynchronous Event Orchestration:** Google Cloud Pub/Sub with dead-letter queue (DLQ) support and worker idempotency.
* **Audit & Compliance:** Structured audit trails, access review certifications, and security anomaly detection.

*Note: Built with mock adapters and local demo cryptography. Does not connect to live corporate IdPs or customer environments.*
    """,
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# 1. Install Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# 2. Install Correlation ID propagation
app.add_middleware(CorrelationIdMiddleware)

# 3. Install Rate Limiter
app.add_middleware(RateLimitMiddleware, max_requests_per_minute=200)

# 4. CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Global Exception Handlers ensuring consistent, safe error envelopes
@app.exception_handler(SecurityException)
async def security_exception_handler(request: Request, exc: SecurityException):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Consult server logs with correlation ID for details.",
        },
    )


# Attach Routes
app.include_router(health_router)
app.include_router(api_v1_router)
app.include_router(worker_router)

# Serve Frontend Dashboard
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", response_class=FileResponse, include_in_schema=False)
    @app.get("/dashboard", response_class=FileResponse, include_in_schema=False)
    async def serve_dashboard():
        """Serves the interactive web control center UI."""
        return FileResponse(STATIC_DIR / "index.html")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
