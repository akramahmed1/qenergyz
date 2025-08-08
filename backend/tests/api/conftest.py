"""
Test Configuration

Test fixtures and configuration for API tests.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
import asyncio
from typing import AsyncGenerator

from api.main import create_app
from api.models.database import Base
from api.dependencies.database import get_db
from api.utils.config import Settings


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture
async def test_db_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def test_settings():
    """Test settings"""
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key="test-secret-key",
        encryption_key="test-encryption-key",
        redis_url="redis://localhost:6379/1",
        environment="testing",
        debug=True,
        # Disable rate limiting for tests
        rate_limit_per_minute=1000,
        rate_limit_per_hour=10000
    )


@pytest_asyncio.fixture
async def test_app(test_db_session):
    """Create test FastAPI app"""
    app = create_app()
    
    # Override database dependency
    async def override_get_db():
        yield test_db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client"""
    return TestClient(test_app)