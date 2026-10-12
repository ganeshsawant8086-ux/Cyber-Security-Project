"""Unit tests for JWT generation, validation, and claims checking."""

from datetime import timedelta
import jwt
import pytest

from src.core.config import settings
from src.core.security import (
    SecurityException,
    create_access_token,
    verify_access_token,
)


def test_valid_token_verification():
    """Verify that a correctly signed token with required claims passes validation."""
    token = create_access_token(
        subject="usr-test-123",
        roles=["security_engineer"],
        email="test@example.com",
        additional_claims={"department": "Security"},
    )

    claims = verify_access_token(token)
    assert claims["sub"] == "usr-test-123"
    assert claims["email"] == "test@example.com"
    assert "security_engineer" in claims["roles"]
    assert claims["department"] == "Security"
    assert claims["iss"] == settings.JWT_ISSUER
    assert claims["aud"] == settings.JWT_AUDIENCE


def test_expired_token_rejected():
    """Verify that an expired JWT raises SecurityException with TOKEN_EXPIRED."""
    expired_token = create_access_token(
        subject="usr-test-123",
        roles=["security_engineer"],
        email="test@example.com",
        expires_delta=timedelta(seconds=-10),
    )

    with pytest.raises(SecurityException) as exc_info:
        verify_access_token(expired_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "TOKEN_EXPIRED"


def test_invalid_issuer_rejected():
    """Verify that a token with an untrusted issuer is rejected."""
    bad_issuer_token = create_access_token(
        subject="usr-test-123",
        roles=["engineer"],
        email="test@example.com",
        custom_issuer="urn:untrusted:attacker-service",
    )

    with pytest.raises(SecurityException) as exc_info:
        verify_access_token(bad_issuer_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "INVALID_ISSUER"


def test_invalid_audience_rejected():
    """Verify that a token minted for a different audience is rejected."""
    bad_aud_token = create_access_token(
        subject="usr-test-123",
        roles=["engineer"],
        email="test@example.com",
        custom_audience="urn:different:client-audience",
    )

    with pytest.raises(SecurityException) as exc_info:
        verify_access_token(bad_aud_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "INVALID_AUDIENCE"


def test_tampered_signature_rejected():
    """Verify that altering the token payload causes signature verification to fail."""
    token = create_access_token(
        subject="usr-test-123",
        roles=["engineer"],
        email="test@example.com",
    )
    tampered_token = token[:-4] + "fake"

    with pytest.raises(SecurityException) as exc_info:
        verify_access_token(tampered_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "INVALID_TOKEN"


def test_missing_required_roles_claim_rejected():
    """Verify that tokens missing mandatory authorization claims are rejected."""
    # Mint token omitting the required 'roles' claim
    payload = {
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "sub": "usr-test-no-roles",
        "exp": 9999999999,
    }
    raw_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

    with pytest.raises(SecurityException) as exc_info:
        verify_access_token(raw_token)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error"] == "MISSING_CLAIM"
