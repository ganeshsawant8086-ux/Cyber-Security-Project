"""Application Configuration and Security Settings.

Demonstrates production configuration patterns:
- Explicit validation of settings using Pydantic v2
- Clear separation between development fallbacks and production requirements
- Secret Manager integration pattern documented for GCP deployments
"""

import os
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Platform configuration settings."""

    # Application metadata
    APP_NAME: str = "identity-access-orchestrator"
    ENVIRONMENT: str = Field(default="development", description="Runtime environment: development, staging, production")
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API Networking
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Security & JWT Configuration
    # NOTE FOR INTERVIEWS & SECURITY AUDITS:
    # In production, keys must be loaded from GCP Secret Manager / Cloud KMS or verified via OIDC JWKS endpoints.
    # A local symmetric key is used here strictly for local demonstration purposes.
    JWT_SECRET_KEY: str = Field(
        default="demo-insecure-secret-key-change-in-production-only-32bytes-min",
        description="Demo HMAC secret key. Must be overridden in production."
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ISSUER: str = "urn:identity-orchestrator:demo-auth-service"
    JWT_AUDIENCE: str = "urn:identity-orchestrator:api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # PostgreSQL Database
    # Supports postgresql+asyncpg:// or sqlite+aiosqlite:// for zero-dependency local test execution
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./demo_identity.db",
        description="Async database connection string"
    )

    # Open Policy Agent (OPA)
    OPA_URL: str = Field(default="http://localhost:8181", description="URL for Open Policy Agent REST API")
    OPA_POLICY_PATH: str = "v1/data/identity/authz"
    OPA_TIMEOUT_SECONDS: float = 3.0

    # Google Cloud Pub/Sub
    GCP_PROJECT_ID: str = "demo-cloud-security-project"
    PUBSUB_TOPIC_LIFECYCLE: str = "identity-lifecycle-events"
    PUBSUB_SUBSCRIPTION_LIFECYCLE: str = "identity-lifecycle-worker-sub"
    PUBSUB_TOPIC_DLQ: str = "identity-lifecycle-dlq"
    PUBSUB_SUBSCRIPTION_DLQ: str = "identity-lifecycle-dlq-sub"
    PUBSUB_EMULATOR_HOST: Optional[str] = None

    # Downstream Integration Emulation
    PROVISIONER_MODE: str = "mock"  # mock or strict
    DOWNSTREAM_TIMEOUT_SECONDS: float = 5.0
    MAX_RETRY_ATTEMPTS: int = 3

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Enforce minimum key strength even in demo mode."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long for cryptographic security.")
        return v


# Singleton instance
settings = Settings()
