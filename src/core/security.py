"""Authentication and JWT validation module.

Demonstrates OAuth2/OIDC standards:
- Validates signature, issuer, audience, expiration, not-before, and required claims.
- Decoupled token verification dependency for FastAPI routers.

SECURITY NOTE:
This project demonstrates token verification patterns locally using symmetric HMAC (HS256)
or mock keys for self-contained testing. In a production environment:
1. Production uses asymmetric cryptography (RS256 / ES256).
2. The verification key is dynamically fetched from an Identity Provider (IdP) JWKS endpoint
   (e.g., Okta, Microsoft Entra ID, Google Cloud Identity).
3. Secret materials are fetched from GCP Secret Manager or Cloud KMS.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("security")
security_scheme = HTTPBearer(auto_error=False)


class SecurityException(HTTPException):
    """Base exception for security and authentication failures."""
    def __init__(self, status_code: int, detail: str, error_code: str):
        super().__init__(status_code=status_code, detail={"error": error_code, "message": detail})


def create_access_token(
    subject: str,
    roles: List[str],
    email: str,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
    custom_issuer: Optional[str] = None,
    custom_audience: Optional[str] = None,
) -> str:
    """Generate a signed JWT token demonstrating OIDC/OAuth2 standard claims."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    claims: Dict[str, Any] = {
        "iss": custom_issuer or settings.JWT_ISSUER,
        "aud": custom_audience or settings.JWT_AUDIENCE,
        "sub": subject,
        "email": email,
        "roles": roles,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }

    if additional_claims:
        claims.update(additional_claims)

    encoded_jwt = jwt.encode(claims, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """Strictly validate JWT signature, issuer, audience, expiration, and required claims."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            audience=settings.JWT_AUDIENCE,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "require": ["exp", "iss", "aud", "sub", "roles"],
            },
        )
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token validation failed: token has expired")
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token signature has expired.",
            error_code="TOKEN_EXPIRED",
        )
    except jwt.InvalidIssuerError:
        logger.warning("Token validation failed: invalid issuer")
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token issuer is invalid.",
            error_code="INVALID_ISSUER",
        )
    except jwt.InvalidAudienceError:
        logger.warning("Token validation failed: invalid audience")
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token audience is invalid.",
            error_code="INVALID_AUDIENCE",
        )
    except jwt.MissingRequiredClaimError as exc:
        logger.warning(f"Token validation failed: missing claim {exc.claim}")
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token missing required claim: {exc.claim}",
            error_code="MISSING_CLAIM",
        )
    except jwt.PyJWTError as exc:
        logger.warning(f"Token validation failed: {str(exc)}")
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            error_code="INVALID_TOKEN",
        )


async def get_current_user(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(security_scheme),
) -> Dict[str, Any]:
    """FastAPI Dependency to authenticate bearer token and extract claims."""
    if not auth_header or not auth_header.credentials:
        raise SecurityException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header with Bearer token.",
            error_code="AUTHENTICATION_REQUIRED",
        )

    claims = verify_access_token(auth_header.credentials)
    return claims


def require_role(required_role: str):
    """Role-based authorization guard for FastAPI routes."""
    def role_checker(claims: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        user_roles = claims.get("roles", [])
        if required_role not in user_roles and "admin" not in user_roles:
            logger.warning(
                f"Access denied for actor {claims.get('sub')}: requires role '{required_role}'"
            )
            raise SecurityException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires role: {required_role}",
                error_code="INSUFFICIENT_PERMISSIONS",
            )
        return claims

    return role_checker
