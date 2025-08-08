"""
Basic API Tests

Simple tests for core API functionality without external dependencies.
"""

import pytest
from fastapi.testclient import TestClient


def test_health_endpoint():
    """Test basic health endpoint without database"""
    from api.main import create_app
    
    # Create a minimal app for testing
    app = create_app()
    client = TestClient(app)
    
    # Override dependencies to skip database and Redis
    from api.dependencies.rate_limiting import limiter
    from api.dependencies.database import get_db
    
    # Mock database dependency
    async def mock_get_db():
        yield None
    
    app.dependency_overrides[get_db] = mock_get_db
    
    # Disable rate limiting
    app.state.limiter = None
    
    # Test health endpoint
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_openapi_documentation():
    """Test that OpenAPI documentation is available"""
    from api.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Override dependencies
    from api.dependencies.database import get_db
    
    async def mock_get_db():
        yield None
    
    app.dependency_overrides[get_db] = mock_get_db
    app.state.limiter = None
    
    # Test OpenAPI endpoint
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    
    openapi_data = response.json()
    assert openapi_data["info"]["title"] == "Qenergyz ETRM API"
    assert "paths" in openapi_data
    assert "/api/v1/auth/register" in openapi_data["paths"]
    assert "/api/v1/auth/login" in openapi_data["paths"]


def test_cors_headers():
    """Test CORS headers are properly set"""
    from api.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Override dependencies
    from api.dependencies.database import get_db
    
    async def mock_get_db():
        yield None
    
    app.dependency_overrides[get_db] = mock_get_db
    app.state.limiter = None
    
    # Make an OPTIONS request to test CORS
    response = client.options("/health", headers={"Origin": "http://localhost:3000"})
    
    # CORS headers should be present
    assert "access-control-allow-origin" in [h.lower() for h in response.headers.keys()]


def test_password_validation():
    """Test password validation utility"""
    from api.dependencies.auth import PasswordHandler
    
    # Test strong password
    result = PasswordHandler.validate_password_strength("SecurePassword123!")
    assert result["valid"] is True
    assert len(result["errors"]) == 0
    
    # Test weak password
    result = PasswordHandler.validate_password_strength("weak")
    assert result["valid"] is False
    assert len(result["errors"]) > 0
    
    # Test password with no uppercase
    result = PasswordHandler.validate_password_strength("nouppercase123!")
    assert result["valid"] is False
    assert "uppercase" in " ".join(result["errors"]).lower()


def test_input_sanitization():
    """Test input sanitization utilities"""
    from api.dependencies.validation import InputSanitizer
    
    # Test HTML sanitization
    dirty_html = "<script>alert('xss')</script><p>Clean content</p>"
    clean_html = InputSanitizer.sanitize_html(dirty_html)
    assert "script" not in clean_html
    assert "Clean content" in clean_html
    
    # Test text sanitization
    dirty_text = "<script>alert('xss')</script>Normal text"
    clean_text = InputSanitizer.sanitize_text(dirty_text) 
    assert "&lt;script&gt;" in clean_text or "script" not in clean_text
    assert "Normal text" in clean_text
    
    # Test email validation
    assert InputSanitizer.validate_email("test@example.com") is True
    assert InputSanitizer.validate_email("invalid-email") is False
    
    # Test phone validation
    assert InputSanitizer.validate_phone("+1-234-567-8900") is True
    assert InputSanitizer.validate_phone("123") is False


def test_jwt_token_utilities():
    """Test JWT token creation and validation"""
    from api.dependencies.auth import JWTHandler
    
    # Create token
    data = {"sub": "user123", "email": "test@example.com"}
    token = JWTHandler.create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are typically quite long
    
    # Validate token
    token_data = JWTHandler.verify_token(token)
    assert token_data.user_id == "user123"
    assert token_data.type == "access"
    assert token_data.payload["email"] == "test@example.com"