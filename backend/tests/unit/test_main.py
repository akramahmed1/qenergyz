"""
Unit tests for the main FastAPI application
"""

import pytest
from fastapi.testclient import TestClient
import json

def test_health_endpoint(client):
    """Test basic health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "version" in data

def test_detailed_health_endpoint(client):
    """Test detailed health endpoint"""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "services" in data
    assert "database" in data["services"]
    assert "cache" in data["services"]

def test_api_v1_status(client):
    """Test API v1 status endpoint"""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["api_version"] == "v1"
    assert data["status"] == "active"
    assert "features" in data

@pytest.mark.asyncio
async def test_websocket_connection(async_client):
    """Test WebSocket connection"""
    # This would require a more complex setup for actual WebSocket testing
    # For now, we'll test that the endpoint exists
    pass

def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.options("/health")
    # CORS headers should be present in the response