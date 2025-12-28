import pytest
from datetime import datetime, timezone, timedelta
import hashlib

from modules.web.services.auth_service import AuthService
from shared.models.users_model import UsersModel


pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestAuthServiceIntegration:
    @pytest.fixture
    def auth_service(self, users_collection, auth_sessions_collection) -> AuthService:
        service = AuthService(collection=users_collection)
        service._sessions_collection = auth_sessions_collection
        return service

    def test_register_new_user(self, auth_service: AuthService):
        result = auth_service.register(
            name="Integration User",
            email="integration@example.com",
            password="secure_password123"
        )

        assert result is not None
        assert result["name"] == "Integration User"
        assert result["email"] == "integration@example.com"
        assert "user_id" in result

    def test_register_duplicate_email(self, auth_service: AuthService):
        auth_service.register("User One", "duplicate@example.com", "password1")

        result = auth_service.register("User Two", "duplicate@example.com", "password2")

        assert result is None

    def test_register_normalizes_email(self, auth_service: AuthService):
        result = auth_service.register(
            name="Test User",
            email="  TEST@EXAMPLE.COM  ",
            password="password"
        )

        assert result["email"] == "test@example.com"

    def test_login_success(self, auth_service: AuthService):
        auth_service.register("Login User", "login@example.com", "correct_password")

        token = auth_service.login("login@example.com", "correct_password")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20

    def test_login_wrong_password(self, auth_service: AuthService):
        auth_service.register("Wrong Pass User", "wrong@example.com", "correct_password")

        token = auth_service.login("wrong@example.com", "wrong_password")

        assert token is None

    def test_login_nonexistent_user(self, auth_service: AuthService):
        token = auth_service.login("nonexistent@example.com", "password")

        assert token is None

    def test_login_email_case_insensitive(self, auth_service: AuthService):
        auth_service.register("Case User", "case@example.com", "password")

        token = auth_service.login("CASE@EXAMPLE.COM", "password")

        assert token is not None

    def test_get_user_by_token(self, auth_service: AuthService):
        auth_service.register("Token User", "token@example.com", "password")
        token = auth_service.login("token@example.com", "password")

        user = auth_service.get_user_by_token(token)

        assert user is not None
        assert isinstance(user, UsersModel)
        assert user.email == "token@example.com"

    def test_get_user_by_invalid_token(self, auth_service: AuthService):
        user = auth_service.get_user_by_token("invalid_token_12345")

        assert user is None

    def test_get_user_by_expired_token(self, auth_service: AuthService, auth_sessions_collection):
        auth_service.register("Expired User", "expired@example.com", "password")
        token = auth_service.login("expired@example.com", "password")

        auth_sessions_collection.update_one(
            {"token": token},
            {"$set": {"expires_at": datetime.now(timezone.utc) - timedelta(hours=1)}}
        )

        user = auth_service.get_user_by_token(token)

        assert user is None

    def test_logout(self, auth_service: AuthService):
        auth_service.register("Logout User", "logout@example.com", "password")
        token = auth_service.login("logout@example.com", "password")

        result = auth_service.logout(token)
        user_after_logout = auth_service.get_user_by_token(token)

        assert result is True
        assert user_after_logout is None

    def test_logout_invalid_token(self, auth_service: AuthService):
        result = auth_service.logout("invalid_token")

        assert result is False

    def test_get_user_by_id(self, auth_service: AuthService):
        registered = auth_service.register("ID User", "id@example.com", "password")

        user = auth_service.get_user_by_id(registered["user_id"])

        assert user is not None
        assert user["email"] == "id@example.com"

    def test_get_user_by_id_not_found(self, auth_service: AuthService):
        user = auth_service.get_user_by_id("nonexistent_user_id")

        assert user is None

    def test_multiple_sessions_same_user(self, auth_service: AuthService):
        auth_service.register("Multi Session", "multi@example.com", "password")

        token1 = auth_service.login("multi@example.com", "password")
        token2 = auth_service.login("multi@example.com", "password")

        assert token1 != token2
        assert auth_service.get_user_by_token(token1) is not None
        assert auth_service.get_user_by_token(token2) is not None

    def test_logout_one_session_keeps_other(self, auth_service: AuthService):
        auth_service.register("Keep Session", "keep@example.com", "password")
        token1 = auth_service.login("keep@example.com", "password")
        token2 = auth_service.login("keep@example.com", "password")

        auth_service.logout(token1)

        assert auth_service.get_user_by_token(token1) is None
        assert auth_service.get_user_by_token(token2) is not None

    def test_password_hashing(self, auth_service: AuthService, users_collection):
        auth_service.register("Hash User", "hash@example.com", "plain_password")

        user_doc = users_collection.find_one({"email": "hash@example.com"})

        assert user_doc["password"] != "plain_password"
        assert user_doc["password"] == hashlib.sha256(b"plain_password").hexdigest()
