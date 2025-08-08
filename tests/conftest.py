"""
Shared pytest fixtures and configuration for Qenergyz Testing Suite
"""
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from unittest.mock import Mock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient


# Test environment configuration
@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables"""
    os.environ.update({
        "TESTING": "true",
        "DATABASE_URL": "sqlite:///./test.db",
        "REDIS_URL": "redis://localhost:6379/1",
        "LOG_LEVEL": "DEBUG",
        "SECRET_KEY": "test-secret-key-for-testing-only",
    })
    return os.environ


# Database fixtures
@pytest.fixture(scope="session")
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    
    yield f"sqlite:///{db_path}"
    
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


# Application fixtures
@pytest.fixture
def mock_app():
    """Mock FastAPI application for testing"""
    from fastapi import FastAPI
    
    app = FastAPI(title="Test Qenergyz API", version="test")
    
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "service": "qenergyz-test"}
    
    @app.get("/ready")
    async def readiness_check():
        return {"status": "ready", "service": "qenergyz-test"}
    
    return app


@pytest.fixture
def client(mock_app):
    """Synchronous test client"""
    return TestClient(mock_app)


@pytest.fixture
async def async_client(mock_app) -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client"""
    async with AsyncClient(app=mock_app, base_url="http://test") as ac:
        yield ac


# Service mocks
@pytest.fixture
def mock_trading_service():
    """Mock trading service for testing"""
    service = Mock()
    service.get_positions.return_value = []
    service.create_trade.return_value = {"id": "test-trade-1", "status": "pending"}
    service.get_market_data.return_value = {"price": 100.0, "volume": 1000}
    return service


@pytest.fixture
def mock_risk_service():
    """Mock risk management service for testing"""
    service = Mock()
    service.calculate_var.return_value = {"var_95": 1000.0, "var_99": 1500.0}
    service.get_risk_metrics.return_value = {"exposure": 50000, "utilization": 0.3}
    return service


@pytest.fixture
def mock_iot_service():
    """Mock IoT service for testing"""
    service = Mock()
    service.get_sensor_data.return_value = {
        "temperature": 25.5,
        "pressure": 101.3,
        "flow_rate": 150.0,
        "timestamp": "2024-01-01T00:00:00Z"
    }
    return service


# Data fixtures
@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "id": "test-user-1",
        "email": "test@qenergyz.com",
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "role": "trader",
        "is_active": True
    }


@pytest.fixture
def sample_trade_data():
    """Sample trade data for testing"""
    return {
        "id": "trade-1",
        "symbol": "WTI",
        "side": "buy",
        "quantity": 1000,
        "price": 75.50,
        "trade_date": "2024-01-01",
        "status": "executed"
    }


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    return {
        "symbol": "WTI",
        "bid": 75.25,
        "ask": 75.50,
        "last": 75.30,
        "volume": 150000,
        "timestamp": "2024-01-01T12:00:00Z"
    }


# Network/HTTP fixtures
@pytest.fixture
def mock_external_api():
    """Mock external API responses"""
    return {
        "market_data_api": {
            "status": "success",
            "data": {"price": 75.50, "volume": 1000}
        },
        "compliance_api": {
            "status": "approved",
            "reference": "COMP-2024-001"
        }
    }


# Performance testing fixtures
@pytest.fixture
def performance_thresholds():
    """Performance testing thresholds"""
    return {
        "api_response_time": 200,  # ms
        "database_query_time": 100,  # ms
        "memory_usage_limit": 512,  # MB
        "cpu_usage_limit": 80  # %
    }


# Security testing fixtures
@pytest.fixture
def security_test_payloads():
    """Security test payloads for vulnerability testing"""
    return {
        "xss_payloads": [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>"
        ],
        "sql_injection_payloads": [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users--"
        ],
        "command_injection_payloads": [
            "; ls -la",
            "| whoami",
            "& ping -c 1 127.0.0.1"
        ]
    }


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Automatically cleanup test files after each test"""
    yield
    
    # Cleanup any test files created during testing
    test_files = [
        "./test.db",
        "./test.log",
        "./test_output.json"
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            os.unlink(file_path)


# Event loop fixture for async tests
@pytest_asyncio.fixture
async def event_loop():
    """Create an event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Test markers configuration
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure custom pytest markers"""
    config.addinivalue_line(
        "markers", "smoke: Basic smoke tests for service health"
    )
    config.addinivalue_line(
        "markers", "functional: Functional tests for business logic"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests between services"
    )
    config.addinivalue_line(
        "markers", "e2e: End-to-end user workflow tests"
    )
    config.addinivalue_line(
        "markers", "load: Load and performance tests"
    )
    config.addinivalue_line(
        "markers", "security: Security and vulnerability tests"
    )
    config.addinivalue_line(
        "markers", "regression: Regression tests"
    )
    config.addinivalue_line(
        "markers", "chaos: Chaos engineering and fault injection tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow-running tests (>30 seconds)"
    )
    config.addinivalue_line(
        "markers", "skip_ci: Skip in CI environment"
    )