"""
Test configuration for Qenergyz backend services
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock
from typing import AsyncGenerator, Dict, Any

import httpx
from fastapi.testclient import TestClient

# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "true"
os.environ["DB_URL"] = "postgresql://test:test@localhost:5432/qenergyz_test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["MOCK_MODE"] = "true"

# Import after setting environment
from src.main import app
from src.config import get_settings
from src.services.trading import TradingService
from src.services.risk import RiskService
from src.services.compliance import ComplianceService
from src.services.iot import IoTService

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def client():
    """Create a test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def async_client():
    """Create an async test client"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def settings():
    """Get test settings"""
    return get_settings()

@pytest.fixture
def mock_trading_service():
    """Mock trading service"""
    service = Mock(spec=TradingService)
    service.initialize = AsyncMock()
    service.shutdown = AsyncMock()
    service.place_order = AsyncMock()
    service.cancel_order = AsyncMock()
    service.get_market_data = AsyncMock()
    service.handle_websocket_message = AsyncMock()
    return service

@pytest.fixture
def mock_risk_service():
    """Mock risk service"""
    service = Mock(spec=RiskService)
    service.initialize = AsyncMock()
    service.shutdown = AsyncMock()
    service.calculate_portfolio_risk = AsyncMock()
    service.run_stress_test = AsyncMock()
    service.monitor_positions = AsyncMock(return_value=[])
    service.handle_websocket_message = AsyncMock()
    return service

@pytest.fixture
def mock_compliance_service():
    """Mock compliance service"""
    service = Mock(spec=ComplianceService)
    service.initialize = AsyncMock()
    service.shutdown = AsyncMock()
    service.validate_transaction = AsyncMock()
    service.perform_kyc = AsyncMock()
    service.monitor_aml_patterns = AsyncMock()
    service.run_periodic_checks = AsyncMock(return_value=[])
    service.handle_websocket_message = AsyncMock()
    return service

@pytest.fixture
def mock_iot_service():
    """Mock IoT service"""
    service = Mock(spec=IoTService)
    service.initialize = AsyncMock()
    service.shutdown = AsyncMock()
    service.register_device = AsyncMock()
    service.read_device_data = AsyncMock()
    service.send_device_command = AsyncMock()
    service.get_device_status = AsyncMock()
    service.handle_websocket_message = AsyncMock()
    return service

@pytest.fixture
def sample_trading_order():
    """Sample trading order data"""
    return {
        "instrument_symbol": "WTI",
        "order_type": "market",
        "side": "buy",
        "quantity": 100.0,
        "trader_id": "test_trader",
        "portfolio_id": "test_portfolio"
    }

@pytest.fixture
def sample_iot_device():
    """Sample IoT device data"""
    return {
        "name": "Test Oil Rig",
        "device_type": "oil_rig",
        "protocol": "mqtt",
        "connection_string": "mqtt://localhost:1883",
        "location": {"lat": 25.2048, "lon": 55.2708}
    }

@pytest.fixture
def sample_customer_data():
    """Sample customer data for KYC"""
    return {
        "customer_id": "test_customer_001",
        "full_name": "John Doe",
        "email": "john.doe@example.com",
        "phone_number": "+1234567890",
        "nationality": "US",
        "address": "123 Main St, City, State"
    }

@pytest.fixture
def mock_external_apis():
    """Mock external API responses"""
    return {
        "nymex": {"price": 75.50, "volume": 1000000},
        "worldcheck": {"matches": [], "risk_score": 0.1},
        "market_data": {"WTI": {"price": 75.50, "bid": 75.45, "ask": 75.55}}
    }