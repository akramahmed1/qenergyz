"""
Integration Tests for API

End-to-end tests for the Qenergyz API functionality.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio

from api.models.user import User, UserRole
from api.dependencies.auth import PasswordHandler


class TestAPIIntegration:
    """Integration tests for complete API workflows"""
    
    @pytest.mark.asyncio
    async def test_user_registration_and_login_flow(self, test_client: TestClient, test_db_session: AsyncSession):
        """Test complete user registration and login workflow"""
        
        # Step 1: Register a new user
        user_data = {
            "email": "integration@test.com",
            "password": "IntegrationTest123!",
            "first_name": "Integration",
            "last_name": "Test",
            "company": "Test Company",
            "job_title": "QA Engineer"
        }
        
        register_response = test_client.post("/api/v1/auth/register", json=user_data)
        assert register_response.status_code == 200
        
        register_data = register_response.json()
        assert register_data["email"] == user_data["email"]
        assert "user_id" in register_data
        
        # Step 2: Verify user was created in database
        user_id = register_data["user_id"]
        result = await test_db_session.execute(
            select(User).where(User.id == user_id)
        )
        created_user = result.scalar_one_or_none()
        
        assert created_user is not None
        assert created_user.email == user_data["email"]
        assert created_user.first_name == user_data["first_name"]
        assert created_user.role == UserRole.USER
        assert created_user.is_active is True
        assert created_user.is_verified is False  # Email verification required
        
        # Step 3: Manually verify user for login test
        created_user.is_verified = True
        await test_db_session.commit()
        
        # Step 4: Login with registered credentials
        login_data = {
            "username": user_data["email"],  # OAuth2 uses username field
            "password": user_data["password"]
        }
        
        login_response = test_client.post("/api/v1/auth/login", data=login_data)
        assert login_response.status_code == 200
        
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert login_result["token_type"] == "bearer"
        assert login_result["user"]["email"] == user_data["email"]
        
        # Step 5: Use access token to get user info
        access_token = login_result["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        
        me_response = test_client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        user_info = me_response.json()
        assert user_info["email"] == user_data["email"]
        assert user_info["first_name"] == user_data["first_name"]
        assert user_info["role"] == "user"
        assert user_info["is_verified"] is True
        
        # Step 6: Change password
        password_change_data = {
            "current_password": user_data["password"],
            "new_password": "NewIntegrationTest456!"
        }
        
        change_password_response = test_client.post(
            "/api/v1/auth/change-password",
            json=password_change_data,
            headers=headers
        )
        assert change_password_response.status_code == 200
        
        # Step 7: Login with new password
        new_login_data = {
            "username": user_data["email"],
            "password": "NewIntegrationTest456!"
        }
        
        new_login_response = test_client.post("/api/v1/auth/login", data=new_login_data)
        assert new_login_response.status_code == 200
        
        # Step 8: Verify old password doesn't work
        old_login_response = test_client.post("/api/v1/auth/login", data=login_data)
        assert old_login_response.status_code == 401
    
    def test_api_endpoints_without_auth(self, test_client: TestClient):
        """Test public API endpoints"""
        
        # Health check should work without authentication
        response = test_client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        
        # API status should work without authentication
        response = test_client.get("/api/v1/status")
        assert response.status_code == 200
        
        data = response.json()
        assert data["api_version"] == "v1"
        assert data["status"] == "active"
        assert "authentication" in data["features"]
    
    def test_protected_endpoints_require_auth(self, test_client: TestClient):
        """Test that protected endpoints require authentication"""
        
        # Try to access protected endpoint without token
        response = test_client.get("/api/v1/auth/me")
        assert response.status_code == 403  # Should require authentication
        
        # Try with invalid token
        headers = {"Authorization": "Bearer invalid-token"}
        response = test_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
    
    def test_rate_limiting(self, test_client: TestClient):
        """Basic test for rate limiting (simplified)"""
        
        # Make multiple requests to API status endpoint
        responses = []
        for i in range(5):
            response = test_client.get("/api/v1/status")
            responses.append(response.status_code)
        
        # All should succeed (rate limit is high for testing)
        assert all(status == 200 for status in responses)
    
    def test_input_validation(self, test_client: TestClient):
        """Test input validation on registration"""
        
        # Test with invalid email
        invalid_email_data = {
            "email": "invalid-email",
            "password": "ValidPassword123!",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = test_client.post("/api/v1/auth/register", json=invalid_email_data)
        assert response.status_code == 422  # Validation error
        
        # Test with weak password
        weak_password_data = {
            "email": "test@valid.com",
            "password": "weak",
            "first_name": "Test",
            "last_name": "User"
        }
        
        response = test_client.post("/api/v1/auth/register", json=weak_password_data)
        assert response.status_code == 400
        assert "Password requirements not met" in response.json()["detail"]
        
        # Test with missing required fields
        incomplete_data = {
            "email": "test@valid.com"
            # Missing password and names
        }
        
        response = test_client.post("/api/v1/auth/register", json=incomplete_data)
        assert response.status_code == 422  # Validation error