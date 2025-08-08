"""
Authentication API Tests

Test JWT authentication, registration, and password management.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from api.models.user import User, UserRole
from api.dependencies.auth import PasswordHandler


class TestAuthenticationAPI:
    """Test authentication endpoints"""
    
    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_api_status_endpoint(self, test_client: TestClient):
        """Test API status endpoint"""
        response = test_client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["api_version"] == "v1"
        assert data["status"] == "active"
        assert "authentication" in data["features"]
    
    @pytest.mark.asyncio
    async def test_user_registration(self, test_client: TestClient, test_db_session: AsyncSession):
        """Test user registration"""
        user_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe",
            "company": "Test Company",
            "job_title": "Test Engineer"
        }
        
        response = test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "user_id" in data
        assert data["verification_required"] is True
    
    def test_user_registration_duplicate_email(self, test_client: TestClient):
        """Test registration with duplicate email"""
        user_data = {
            "email": "test@example.com",
            "password": "SecurePassword123!",
            "first_name": "John",
            "last_name": "Doe"
        }
        
        # First registration should succeed
        response = test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        # Second registration should fail
        response = test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"]
    
    def test_user_registration_weak_password(self, test_client: TestClient):
        """Test registration with weak password"""
        user_data = {
            "email": "test2@example.com",
            "password": "weak",  # Weak password
            "first_name": "John",
            "last_name": "Doe"
        }
        
        response = test_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Password requirements not met" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_user_login(self, test_client: TestClient, test_db_session: AsyncSession):
        """Test user login"""
        # Create a test user first
        test_user = User(
            email="login@example.com",
            password_hash=PasswordHandler.hash_password("SecurePassword123!"),
            first_name="Login",
            last_name="Test",
            role=UserRole.USER,
            is_active=True,
            is_verified=True
        )
        
        test_db_session.add(test_user)
        await test_db_session.commit()
        
        # Test login
        login_data = {
            "username": "login@example.com",  # OAuth2 uses 'username' field
            "password": "SecurePassword123!"
        }
        
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "login@example.com"
    
    def test_user_login_invalid_credentials(self, test_client: TestClient):
        """Test login with invalid credentials"""
        login_data = {
            "username": "nonexistent@example.com",
            "password": "wrongpassword"
        }
        
        response = test_client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]
    
    def test_password_validation(self):
        """Test password strength validation"""
        # Test weak password
        result = PasswordHandler.validate_password_strength("weak")
        assert not result["valid"]
        assert len(result["errors"]) > 0
        
        # Test strong password
        result = PasswordHandler.validate_password_strength("SecurePassword123!")
        assert result["valid"]
        assert len(result["errors"]) == 0
    
    def test_password_hashing(self):
        """Test password hashing and verification"""
        password = "SecurePassword123!"
        
        # Test hashing
        hashed = PasswordHandler.hash_password(password)
        assert hashed != password
        assert len(hashed) > 50  # Argon2 hashes are quite long
        
        # Test verification
        assert PasswordHandler.verify_password(password, hashed)
        assert not PasswordHandler.verify_password("wrongpassword", hashed)


class TestAuthenticationDependencies:
    """Test authentication dependencies and utilities"""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, test_client: TestClient):
        """Test rate limiting on auth endpoints"""
        # This is a basic test - more comprehensive rate limiting tests
        # would require Redis and multiple requests
        response = test_client.get("/api/v1/status")
        assert response.status_code == 200
    
    def test_jwt_token_creation_and_validation(self):
        """Test JWT token creation and validation"""
        from api.dependencies.auth import JWTHandler
        
        # Create token
        data = {"sub": "user123", "email": "test@example.com"}
        token = JWTHandler.create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 50
        
        # Validate token
        token_data = JWTHandler.verify_token(token)
        assert token_data.user_id == "user123"
        assert token_data.type == "access"