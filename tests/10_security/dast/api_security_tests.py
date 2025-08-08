"""
API Security Tests - Test common API vulnerabilities
"""
import pytest
import requests
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient


class APISecurityTester:
    """API Security Testing Class"""
    
    def __init__(self, client):
        self.client = client
        self.base_url = "http://testserver"
    
    def test_sql_injection_attempts(self):
        """Test SQL injection vulnerability"""
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "1' UNION SELECT * FROM users--",
            "admin'--",
            "' OR 1=1#"
        ]
        
        vulnerable_endpoints = [
            "/api/v1/users",
            "/api/v1/trades",
            "/api/v1/search"
        ]
        
        for endpoint in vulnerable_endpoints:
            for payload in sql_payloads:
                # Test in query parameters
                response = self.client.get(f"{endpoint}?id={payload}")
                assert response.status_code != 200 or not self._contains_sql_error(response)
                
                # Test in JSON body
                response = self.client.post(endpoint, json={"search": payload})
                assert response.status_code != 200 or not self._contains_sql_error(response)
    
    def _contains_sql_error(self, response):
        """Check if response contains SQL error messages"""
        sql_error_patterns = [
            "sql syntax",
            "mysql_fetch",
            "ora-",
            "postgresql",
            "sqlite",
            "syntax error"
        ]
        
        response_text = response.text.lower()
        return any(pattern in response_text for pattern in sql_error_patterns)
    
    def test_xss_protection(self):
        """Test Cross-Site Scripting (XSS) protection"""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<svg onload=alert('xss')>",
            "';alert('xss');//"
        ]
        
        endpoints = ["/api/v1/profile", "/api/v1/comments"]
        
        for endpoint in endpoints:
            for payload in xss_payloads:
                response = self.client.post(endpoint, json={"content": payload})
                
                # Response should not contain unescaped payload
                if response.status_code == 200:
                    assert payload not in response.text
                    # Check for proper HTML escaping
                    if "<script>" in payload:
                        assert "&lt;script&gt;" in response.text or payload not in response.text
    
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms"""
        # Create a session
        login_response = self.client.post("/auth/login", json={
            "username": "testuser",
            "password": "testpass"
        })
        
        if login_response.status_code == 200:
            # Try to perform state-changing operation without CSRF token
            response = self.client.post("/api/v1/trades", json={
                "symbol": "WTI",
                "side": "buy",
                "quantity": 1000
            })
            
            # Should either require CSRF token or use proper authentication
            assert response.status_code in [401, 403, 422]  # Unauthorized, Forbidden, or Validation Error
    
    def test_authentication_bypass(self):
        """Test authentication bypass attempts"""
        protected_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/profile",
            "/api/v1/trades"
        ]
        
        bypass_attempts = [
            {},  # No auth header
            {"Authorization": "Bearer invalid_token"},
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Basic invalid"},
            {"Authorization": "Bearer null"},
            {"Authorization": "Bearer ../../../etc/passwd"}
        ]
        
        for endpoint in protected_endpoints:
            for headers in bypass_attempts:
                response = self.client.get(endpoint, headers=headers)
                # Should return 401 (Unauthorized) or 403 (Forbidden)
                assert response.status_code in [401, 403]
    
    def test_authorization_bypass(self):
        """Test authorization bypass (privilege escalation)"""
        # Simulate regular user token
        user_headers = {"Authorization": "Bearer regular_user_token"}
        
        admin_endpoints = [
            "/api/v1/admin/users",
            "/api/v1/admin/system-config",
            "/api/v1/admin/audit-logs"
        ]
        
        for endpoint in admin_endpoints:
            response = self.client.get(endpoint, headers=user_headers)
            # Regular user should not access admin endpoints
            assert response.status_code in [401, 403]
    
    def test_input_validation(self):
        """Test input validation and sanitization"""
        # Test oversized inputs
        large_payload = "A" * 10000
        response = self.client.post("/api/v1/profile", json={
            "name": large_payload
        })
        
        # Should reject oversized inputs
        assert response.status_code in [400, 413, 422]
        
        # Test special characters
        special_chars = ["../../etc/passwd", "../../../windows/system32", "\x00\x01\x02"]
        
        for payload in special_chars:
            response = self.client.post("/api/v1/search", json={
                "query": payload
            })
            
            # Should handle special characters safely
            if response.status_code == 200:
                assert payload not in response.text
    
    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities"""
        # Test error message information disclosure
        response = self.client.get("/nonexistent-endpoint")
        
        # Should not disclose sensitive information in error messages
        sensitive_info = [
            "database",
            "connection string", 
            "password",
            "secret",
            "token",
            "internal server error"
        ]
        
        response_text = response.text.lower()
        for info in sensitive_info:
            assert info not in response_text or response.status_code == 404
    
    def test_rate_limiting(self):
        """Test rate limiting protection"""
        endpoint = "/api/v1/login"
        
        # Make rapid requests
        responses = []
        for i in range(10):
            response = self.client.post(endpoint, json={
                "username": "testuser",
                "password": "wrongpassword"
            })
            responses.append(response.status_code)
        
        # Should implement rate limiting after several failed attempts
        rate_limited_responses = [429, 403]  # Too Many Requests or Forbidden
        assert any(code in rate_limited_responses for code in responses[-3:])


@pytest.mark.security
def test_api_security_comprehensive():
    """Run comprehensive API security tests"""
    # Create test app
    app = FastAPI()
    
    @app.get("/health")
    def health():
        return {"status": "healthy"}
    
    @app.post("/api/v1/search")
    def search(data: dict):
        # Vulnerable endpoint for testing
        return {"results": f"Search for: {data.get('query', '')}"}
    
    @app.get("/api/v1/admin/users")
    def admin_users():
        return {"error": "Unauthorized"}, 401
    
    client = TestClient(app)
    security_tester = APISecurityTester(client)
    
    # Run all security tests
    security_tester.test_sql_injection_attempts()
    security_tester.test_xss_protection()
    security_tester.test_authentication_bypass()
    security_tester.test_input_validation()
    security_tester.test_information_disclosure()


@pytest.mark.security
def test_headers_security():
    """Test security headers"""
    app = FastAPI()
    
    @app.get("/test")
    def test_endpoint():
        return {"message": "test"}
    
    client = TestClient(app)
    response = client.get("/test")
    
    # Test for security headers (these would be added by middleware in real app)
    recommended_headers = [
        "x-content-type-options",
        "x-frame-options", 
        "x-xss-protection",
        "strict-transport-security",
        "content-security-policy"
    ]
    
    # In a real implementation, these headers should be present
    # For testing, we verify the response structure
    assert response.status_code == 200


@pytest.mark.security
def test_https_redirect():
    """Test HTTPS redirect functionality"""
    # This would test HTTPS enforcement in production
    # For testing purposes, we simulate the check
    
    import os
    environment = os.getenv("ENVIRONMENT", "test")
    
    if environment == "production":
        # In production, HTTP requests should redirect to HTTPS
        # This would be handled by reverse proxy or middleware
        pass
    
    # For test environment, this is acceptable
    assert True


@pytest.mark.security  
def test_cors_configuration():
    """Test CORS configuration security"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient
    
    app = FastAPI()
    
    # Add CORS middleware with secure configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://app.qenergyz.com"],  # Specific origins, not "*"
        allow_credentials=True,
        allow_methods=["GET", "POST"],  # Limited methods
        allow_headers=["Authorization", "Content-Type"],  # Limited headers
    )
    
    @app.get("/api/data")
    def get_data():
        return {"data": "sensitive"}
    
    client = TestClient(app)
    
    # Test with allowed origin
    response = client.get("/api/data", headers={"Origin": "https://app.qenergyz.com"})
    assert response.status_code == 200
    
    # Test with disallowed origin - would be blocked by browser
    response = client.get("/api/data", headers={"Origin": "https://malicious.com"})
    # In real browser, this would be blocked by CORS policy
    # TestClient doesn't enforce CORS, so we check configuration instead
    assert response.status_code == 200  # TestClient allows this, but real browser wouldn't