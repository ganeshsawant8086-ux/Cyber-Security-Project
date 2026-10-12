"""Authentication, Token Minting, and Session Inspection Endpoints.

DEMO NOTE:
Demonstrates OAuth2/OIDC token concepts using local cryptographic keys.
Clearly states that production Identity Providers (Okta/Entra ID) are replaced here by a demo token issuer.
"""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, status

from src.core.config import settings
from src.core.security import (
    create_access_token,
    get_current_user,
    verify_access_token,
)
from src.schemas.auth import (
    SessionInspectResponse,
    TokenRequest,
    TokenResponse,
    TokenValidateRequest,
)

auth_router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Token Inspection"])


@auth_router.post("/token", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def generate_demo_token(req: TokenRequest):
    """Generate a signed JWT token demonstrating standard OIDC/OAuth2 claims.

    Use this endpoint to generate tokens for fictional personas:
    - Alice (HR Admin): roles=["hr_admin"]
    - Bob (Identity Admin): roles=["identity_admin"]
    - Charlie (Standard Engineer): roles=["engineer"]
    - Eve (Restricted Contractor): roles=["contractor"]
    """
    token = create_access_token(
        subject=req.subject,
        roles=req.roles,
        email=req.email,
        additional_claims={"department": req.department, **(req.additional_claims or {})},
    )

    return TokenResponse(
        access_token=token,
        token_type="Bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        issuer=settings.JWT_ISSUER,
        audience=settings.JWT_AUDIENCE,
        scope="identity:lifecycle",
    )


@auth_router.post("/inspect", response_model=SessionInspectResponse, status_code=status.HTTP_200_OK)
async def inspect_token(req: TokenValidateRequest):
    """Inspect and cryptographically validate an arbitrary JWT token.

    Validates signature, issuer, audience, and expiration.
    """
    claims = verify_access_token(req.token)
    exp = claims.get("exp", 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    remaining = max(0, exp - now_ts)

    return SessionInspectResponse(
        valid=True,
        subject=claims.get("sub", ""),
        email=claims.get("email"),
        roles=claims.get("roles", []),
        issuer=claims.get("iss", ""),
        audience=claims.get("aud", ""),
        issued_at=claims.get("iat", 0),
        expires_at=exp,
        remaining_seconds=remaining,
        all_claims=claims,
    )


@auth_router.get("/session", response_model=SessionInspectResponse, status_code=status.HTTP_200_OK)
async def inspect_current_session(claims: Dict[str, Any] = Depends(get_current_user)):
    """Inspect the caller's active session extracted from Authorization: Bearer <token> header."""
    exp = claims.get("exp", 0)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    remaining = max(0, exp - now_ts)

    return SessionInspectResponse(
        valid=True,
        subject=claims.get("sub", ""),
        email=claims.get("email"),
        roles=claims.get("roles", []),
        issuer=claims.get("iss", ""),
        audience=claims.get("aud", ""),
        issued_at=claims.get("iat", 0),
        expires_at=exp,
        remaining_seconds=remaining,
        all_claims=claims,
    )
