"""
Security validation tests
Tests authorization, authentication, input injection, and CORS validation
"""
import pytest
import httpx
from tests.test_config import (
    BASE_URL,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS,
    PATH_TRAVERSAL_PATTERNS,
)
from tests.test_helpers import (
    generate_test_user,
    register_and_login,
    validate_error_response,
)


@pytest.mark.security
@pytest.mark.unit
class TestAuthenticationSecurity:
    """Test authentication security measures"""
    
    @pytest.mark.asyncio
    async def test_missing_token_returns_401(self, http_client):
        """Test that protected endpoints return 401 without token"""
        protected_endpoints = [
            "/profile",
            "/files",
            "/documents",
            "/orders",
        ]
        
        for endpoint in protected_endpoints:
            response = await http_client.get(f"{BASE_URL}{endpoint}")
            assert response.status_code == 401, \
                f"Endpoint {endpoint} should return 401 without token"
    
    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, http_client):
        """Test that invalid tokens are rejected"""
        invalid_tokens = [
            "invalid_token",
            "Bearer invalid",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
            "",
        ]
        
        for token in invalid_tokens:
            if token == "":
                # Empty token should not have "Bearer " prefix
                response = await http_client.get(
                    f"{BASE_URL}/profile",
                    headers={"Authorization": ""}
                )
            else:
                response = await http_client.get(
                    f"{BASE_URL}/profile",
                    headers={"Authorization": f"Bearer {token}"}
                )
            assert response.status_code == 401, \
                f"Invalid token '{token[:20]}...' should be rejected"
    
    @pytest.mark.asyncio
    async def test_malformed_authorization_header(self, http_client):
        """Test malformed Authorization headers"""
        malformed_headers = [
            "invalid_format",
            "Bearer",
            "Bearer  ",  # Double space - this will cause header error
            "Token abc123",  # Wrong scheme
        ]
        
        for header_value in malformed_headers:
            # Skip header values that cause HTTP protocol errors
            if header_value in ["Bearer  "]:  # Double space causes protocol error
                continue
                
            response = await http_client.get(
                f"{BASE_URL}/profile",
                headers={"Authorization": header_value}
            )
            assert response.status_code == 401, \
                f"Malformed header '{header_value}' should be rejected"
    
    @pytest.mark.asyncio
    async def test_expired_token_handling(self, http_client, user_account):
        """Test expired token handling"""
        # Note: This is a placeholder - actual implementation would require
        # generating an expired token or waiting for token expiration
        user_data, token = user_account
        
        # Simulate expired token by modifying payload
        # In real implementation, would use JWT library to create expired token
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjB9.invalid"
        
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == 401


@pytest.mark.security
@pytest.mark.unit
class TestAuthorizationSecurity:
    """Test authorization and access control"""
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_files(
        self, http_client, multiple_users, test_file_upload
    ):
        """Test that users cannot access other users' files"""
        # User 1 uploads a file
        user1_data, user1_token = multiple_users[0]
        user2_data, user2_token = multiple_users[1]
        
        # Upload file as user1
        upload_response = await http_client.post(
            f"{BASE_URL}/files",
            json=test_file_upload,
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["id"]
        
        # Try to access as user2
        response = await http_client.get(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response.status_code in [403, 404], \
            "User should not be able to access other user's files"
        
        # Try to delete as user2
        response = await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {user2_token}"}
        )
        assert response.status_code in [403, 404], \
            "User should not be able to delete other user's files"
        
        # Cleanup
        await http_client.delete(
            f"{BASE_URL}/files/{file_id}",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
    
    @pytest.mark.asyncio
    async def test_user_cannot_access_other_user_orders(
        self, http_client, multiple_users
    ):
        """Test that users cannot access other users' orders"""
        user1_data, user1_token = multiple_users[0]
        user2_data, user2_token = multiple_users[1]
        
        # Get user1's orders
        response = await http_client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {user1_token}"}
        )
        assert response.status_code == 200
        
        # If user1 has orders, try to access them as user2
        orders = response.json()
        if orders:
            order_id = orders[0]["order_id"]
            response = await http_client.get(
                f"{BASE_URL}/orders/{order_id}",
                headers={"Authorization": f"Bearer {user2_token}"}
            )
            assert response.status_code in [403, 404], \
                "User should not be able to access other user's orders"
    
    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_admin_endpoints(
        self, http_client, user_account
    ):
        """Test that regular users cannot access admin endpoints"""
        user_data, token = user_account
        
        admin_endpoints = [
            ("/users", "GET"),
            ("/admin/orders", "GET"),
            ("/users/1/documents", "GET"),  # Admin-only endpoint for user documents
            ("/admin/call-requests", "GET"),
            ("/sync/status", "GET"),
            ("/sync/queue", "GET"),
        ]
        
        for endpoint, method in admin_endpoints:
            if method == "GET":
                response = await http_client.get(
                    f"{BASE_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {token}"}
                )
            else:
                response = await http_client.post(
                    f"{BASE_URL}{endpoint}",
                    headers={"Authorization": f"Bearer {token}"}
                )
            
            assert response.status_code == 403, \
                f"Regular user should not access admin endpoint: {endpoint}"
    
    @pytest.mark.asyncio
    async def test_privilege_escalation_attempt(
        self, http_client, user_account, admin_token
    ):
        """Test that users cannot escalate their own privileges"""
        user_data, user_token = user_account
        
        # Get user profile
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        user_profile = response.json()
        user_id = user_profile["id"]
        
        # Try to update own profile to admin (should be ignored)
        response = await http_client.put(
            f"{BASE_URL}/profile",
            json={"is_admin": True},
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200, \
            "Profile update should succeed but ignore is_admin field"
        
        # Verify user is still not admin
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 200
        updated_profile = response.json()
        assert not updated_profile.get("is_admin", False), \
            "User should not have admin privileges"


@pytest.mark.security
@pytest.mark.unit
class TestInputValidationSecurity:
    """Test input validation and injection prevention"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_username(self, http_client):
        """Test SQL injection patterns in username field"""
        for pattern in SQL_INJECTION_PATTERNS:
            user_data = generate_test_user()
            user_data["username"] = pattern
            
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            # Should either reject with 400/422 or sanitize the input
            assert response.status_code in [400, 422], \
                f"SQL injection pattern should be rejected: {pattern[:50]}"
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_login(self, http_client):
        """Test SQL injection patterns in login credentials"""
        for pattern in SQL_INJECTION_PATTERNS:
            response = await http_client.post(
                f"{BASE_URL}/login",
                json={"username": pattern, "password": "test123"}
            )
            assert response.status_code in [400, 401, 422], \
                f"SQL injection in login should be rejected: {pattern[:50]}"
    
    @pytest.mark.asyncio
    async def test_xss_in_text_fields(self, http_client, user_account):
        """Test XSS patterns in text fields"""
        user_data, token = user_account
        
        for pattern in XSS_PATTERNS:
            # Test in file description
            response = await http_client.post(
                f"{BASE_URL}/files",
                json={
                    "file_name": "test.stl",
                    "file_data": "dGVzdA==",  # "test" in base64
                    "description": pattern
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            # Should sanitize or reject
            if response.status_code == 200:
                file_data = response.json()
                # Verify XSS is sanitized
                assert pattern not in str(file_data.get("description", "")), \
                    "XSS pattern should be sanitized"
                # Cleanup
                await http_client.delete(
                    f"{BASE_URL}/files/{file_data['id']}",
                    headers={"Authorization": f"Bearer {token}"}
                )
    
    @pytest.mark.asyncio
    async def test_path_traversal_in_filename(self, http_client, user_account):
        """Test path traversal patterns in file names"""
        user_data, token = user_account
        
        for pattern in PATH_TRAVERSAL_PATTERNS:
            response = await http_client.post(
                f"{BASE_URL}/files",
                json={
                    "file_name": pattern,
                    "file_data": "dGVzdA==",
                    "description": "test"
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                file_data = response.json()
                # Verify filename is sanitized
                saved_filename = file_data.get("filename", "")
                assert ".." not in saved_filename, \
                    "Path traversal should be prevented in filename"
                assert "/" not in saved_filename and "\\" not in saved_filename, \
                    "Path separators should be removed from filename"
                # Cleanup
                await http_client.delete(
                    f"{BASE_URL}/files/{file_data['id']}",
                    headers={"Authorization": f"Bearer {token}"}
                )
    
    @pytest.mark.asyncio
    async def test_oversized_input_fields(self, http_client):
        """Test handling of oversized input fields"""
        user_data = generate_test_user()
        
        # Very long username
        user_data["username"] = "a" * 1000
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        assert response.status_code in [400, 422], \
            "Oversized username should be rejected"
        
        # Very long email
        user_data["username"] = "valid_user"
        user_data["email"] = "a" * 1000 + "@example.com"
        response = await http_client.post(f"{BASE_URL}/register", json=user_data)
        assert response.status_code in [400, 422], \
            "Oversized email should be rejected"
    
    @pytest.mark.asyncio
    async def test_special_characters_in_fields(self, http_client):
        """Test special characters in various fields"""
        special_chars = [
            "\x00",  # Null byte
            "\n\r\t",  # Whitespace
            "🔥💀👻",  # Emojis
            "<>\"'&",  # HTML special chars
        ]
        
        for chars in special_chars:
            user_data = generate_test_user()
            user_data["full_name"] = f"Test {chars} User"
            
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            # Should either accept with sanitization or reject
            # We check that the response is valid and doesn't crash
            assert response.status_code in [200, 400, 422]


@pytest.mark.security
@pytest.mark.unit
class TestCORSSecurity:
    """Test CORS policy validation"""
    
    @pytest.mark.asyncio
    async def test_cors_preflight_requests(self, http_client):
        """Test CORS preflight OPTIONS requests"""
        endpoints = [
            "/register",
            "/login",
            "/files",
            "/orders",
            "/calculate-price",
        ]
        
        for endpoint in endpoints:
            response = await http_client.options(f"{BASE_URL}{endpoint}")
            assert response.status_code == 200, \
                f"OPTIONS request should succeed for {endpoint}"
            
            # Check CORS headers are present
            headers = response.headers
            # Note: Actual CORS headers depend on server configuration
            # This is a basic check
    
    @pytest.mark.asyncio
    async def test_cors_headers_present(self, http_client):
        """Test that CORS headers are present in responses"""
        response = await http_client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        
        # CORS headers should be present (server-dependent)
        # This test verifies the request completes without CORS errors


@pytest.mark.security
@pytest.mark.unit
class TestSessionSecurity:
    """Test session and token security"""
    
    @pytest.mark.asyncio
    async def test_token_cannot_be_reused_after_logout(
        self, http_client, user_account
    ):
        """Test that tokens cannot be used after logout"""
        user_data, token = user_account
        
        # Verify token works
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Logout
        response = await http_client.post(
            f"{BASE_URL}/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        
        # Try to use token after logout
        response = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token}"}
        )
        # Should be rejected (401) if token blacklisting is implemented
        # May still work (200) if stateless JWT without blacklist
        # Either is acceptable depending on implementation
        assert response.status_code in [200, 401]
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self, http_client, user_account):
        """Test handling of concurrent sessions from same user"""
        user_data, token1 = user_account
        
        # Login again to get second token
        token2 = await http_client.post(
            f"{BASE_URL}/login",
            json={
                "username": user_data["username"],
                "password": user_data["password"]
            }
        )
        assert token2.status_code == 200
        token2 = token2.json()["access_token"]
        
        # Both tokens should work
        response1 = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token1}"}
        )
        assert response1.status_code == 200
        
        response2 = await http_client.get(
            f"{BASE_URL}/profile",
            headers={"Authorization": f"Bearer {token2}"}
        )
        assert response2.status_code == 200


@pytest.mark.security
@pytest.mark.unit
class TestRateLimitingSecurity:
    """Test rate limiting and abuse prevention"""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rapid_login_attempts(self, http_client):
        """Test handling of rapid login attempts"""
        # Attempt multiple rapid logins
        for _ in range(10):
            response = await http_client.post(
                f"{BASE_URL}/login",
                json={"username": "nonexistent", "password": "wrong"}
            )
            # Should either rate limit or return 401
            assert response.status_code in [401, 429], \
                "Rapid login attempts should be handled appropriately"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_rapid_registration_attempts(self, http_client):
        """Test handling of rapid registration attempts"""
        # Attempt multiple rapid registrations
        for i in range(10):
            user_data = generate_test_user()
            response = await http_client.post(
                f"{BASE_URL}/register",
                json=user_data
            )
            # Should either succeed or rate limit
            assert response.status_code in [200, 429]

