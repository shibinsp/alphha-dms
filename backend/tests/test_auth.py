import pytest
from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Test authentication endpoints."""

    def test_login_success(self, client: TestClient, test_user):
        """Test successful login with valid credentials."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "test@alphha.local", "password": "testpassword123"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_email(self, client: TestClient, test_user):
        """Test login with invalid email."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "wrong@alphha.local", "password": "testpassword123"}
        )
        assert response.status_code == 401

    def test_login_invalid_password(self, client: TestClient, test_user):
        """Test login with invalid password."""
        response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "test@alphha.local", "password": "wrongpassword"}
        )
        assert response.status_code == 401

    def test_get_current_user(self, client: TestClient, test_user, auth_headers):
        """Test getting current user info."""
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@alphha.local"
        assert data["full_name"] == "Test User"

    def test_get_current_user_unauthorized(self, client: TestClient):
        """Test getting current user without auth."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    def test_token_refresh(self, client: TestClient, test_user):
        """Test token refresh."""
        # First login
        login_response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "test@alphha.local", "password": "testpassword123"}
        )
        assert login_response.status_code == 200
        tokens = login_response.json()

        # Refresh token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens

    def test_logout(self, client: TestClient, test_user, auth_headers):
        """Test logout."""
        # First login to get tokens
        login_response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "test@alphha.local", "password": "testpassword123"}
        )
        tokens = login_response.json()

        # Logout
        response = client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": tokens["refresh_token"]},
            headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["message"] == "Successfully logged out"


class TestPasswordChange:
    """Test password change functionality."""

    def test_change_password_success(self, client: TestClient, test_user, auth_headers):
        """Test successful password change."""
        response = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": "testpassword123",
                "new_password": "newpassword456"
            },
            headers=auth_headers
        )
        assert response.status_code == 200

        # Verify new password works
        login_response = client.post(
            "/api/v1/auth/login/json",
            json={"email": "test@alphha.local", "password": "newpassword456"}
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_current(self, client: TestClient, test_user, auth_headers):
        """Test password change with wrong current password."""
        response = client.post(
            "/api/v1/auth/password/change",
            json={
                "current_password": "wrongpassword",
                "new_password": "newpassword456"
            },
            headers=auth_headers
        )
        assert response.status_code == 400
