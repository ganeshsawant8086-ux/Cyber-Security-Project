"""Pytest fixtures for unit and integration testing."""

import asyncio
import os
from typing import AsyncGenerator, Dict
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force in-memory SQLite database and test config before importing application code
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["ENVIRONMENT"] = "test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-unit-testing-32bytes-min"
os.environ["PUBSUB_EMULATOR_HOST"] = ""

from src.core.config import settings
from src.core.database import Base, get_db
from src.core.security import create_access_token
from src.main import app
from src.services.pubsub_publisher import publisher

# Test SQLite Engine
test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestAsyncSession = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
def reset_publisher():
    """Clear in-memory publisher queues before each test."""
    publisher.clear()
    yield
    publisher.clear()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provides a clean in-memory database session for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSession() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Test client bound to application with in-memory database override."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def hr_admin_token() -> str:
    """Signed JWT for HR Admin persona (can onboard)."""
    return create_access_token(
        subject="usr-hr-alice",
        roles=["hr_admin"],
        email="alice.hr@example.com",
    )


@pytest.fixture
def identity_admin_token() -> str:
    """Signed JWT for Identity Admin persona (can perform role changes and campaigns)."""
    return create_access_token(
        subject="usr-id-bob",
        roles=["identity_admin"],
        email="bob.identity@example.com",
    )


@pytest.fixture
def engineer_token() -> str:
    """Signed JWT for standard Engineer persona."""
    return create_access_token(
        subject="usr-eng-charlie",
        roles=["engineer"],
        email="charlie.eng@example.com",
    )


@pytest.fixture
def contractor_token() -> str:
    """Signed JWT for external Contractor persona."""
    return create_access_token(
        subject="usr-contractor-eve",
        roles=["contractor"],
        email="eve.contractor@example.com",
    )
