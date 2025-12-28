import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import hashlib

from shared.models.users_model import UsersModel
from modules.web.services.auth_service import AuthService


pytestmark = pytest.mark.unit


class TestAuthService:
    @pytest.fixture
    def mock_sessions_collection(self) -> MagicMock:
        collection = MagicMock()
        collection.find_one = MagicMock(return_value=None)
        collection.insert_one = MagicMock()
        collection.delete_one = MagicMock(return_value=MagicMock(deleted_count=0))
        return collection

    @pytest.fixture
    def auth_service(
        self,
        mock_mongo_collection: MagicMock,
        mock_sessions_collection: MagicMock,
    ) -> AuthService:
        service = AuthService(collection=mock_mongo_collection)
        service._sessions_collection = mock_sessions_collection
        return service

    def test_hash_password(self, auth_service: AuthService):
        password = "test_password"
        hashed = auth_service._hash_password(password)

        expected = hashlib.sha256(password.encode()).hexdigest()
        assert hashed == expected

    def test_register_success(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one.return_value = None

        result = auth_service.register("John Doe", "john@example.com", "password123")

        assert result is not None
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"
        assert "user_id" in result
        mock_mongo_collection.insert_one.assert_called_once()

    def test_register_email_already_exists(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        sample_user_doc: dict,
    ):
        mock_mongo_collection.find_one.return_value = sample_user_doc

        result = auth_service.register("John Doe", "test@example.com", "password123")

        assert result is None
        mock_mongo_collection.insert_one.assert_not_called()

    def test_register_normalizes_email(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one.return_value = None

        result = auth_service.register("John", "  JOHN@EXAMPLE.COM  ", "password")

        assert result["email"] == "john@example.com"

    def test_login_success(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        mock_sessions_collection: MagicMock,
        sample_user_doc: dict,
    ):
        password = "correct_password"
        sample_user_doc["password"] = hashlib.sha256(password.encode()).hexdigest()
        mock_mongo_collection.find_one.return_value = sample_user_doc

        result = auth_service.login("test@example.com", password)

        assert result is not None
        assert isinstance(result, str)
        mock_sessions_collection.insert_one.assert_called_once()

    def test_login_user_not_found(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one.return_value = None

        result = auth_service.login("nonexistent@example.com", "password")

        assert result is None

    def test_login_wrong_password(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        sample_user_doc: dict,
    ):
        sample_user_doc["password"] = hashlib.sha256(b"correct_password").hexdigest()
        mock_mongo_collection.find_one.return_value = sample_user_doc

        result = auth_service.login("test@example.com", "wrong_password")

        assert result is None

    def test_get_user_by_token_success(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        mock_sessions_collection: MagicMock,
        sample_user_doc: dict,
        auth_session_doc: dict,
    ):
        mock_sessions_collection.find_one.return_value = auth_session_doc
        mock_mongo_collection.find_one.return_value = sample_user_doc

        result = auth_service.get_user_by_token(auth_session_doc["token"])

        assert result is not None
        assert isinstance(result, UsersModel)
        assert result.user_id == sample_user_doc["user_id"]

    def test_get_user_by_token_expired_session(
        self,
        auth_service: AuthService,
        mock_sessions_collection: MagicMock,
    ):
        mock_sessions_collection.find_one.return_value = None

        result = auth_service.get_user_by_token("expired_token")

        assert result is None

    def test_get_user_by_token_user_not_found(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        mock_sessions_collection: MagicMock,
        auth_session_doc: dict,
    ):
        mock_sessions_collection.find_one.return_value = auth_session_doc
        mock_mongo_collection.find_one.return_value = None

        result = auth_service.get_user_by_token(auth_session_doc["token"])

        assert result is None

    def test_logout_success(
        self,
        auth_service: AuthService,
        mock_sessions_collection: MagicMock,
    ):
        mock_sessions_collection.delete_one.return_value = MagicMock(deleted_count=1)

        result = auth_service.logout("valid_token")

        assert result is True
        mock_sessions_collection.delete_one.assert_called_once_with({"token": "valid_token"})

    def test_logout_token_not_found(
        self,
        auth_service: AuthService,
        mock_sessions_collection: MagicMock,
    ):
        mock_sessions_collection.delete_one.return_value = MagicMock(deleted_count=0)

        result = auth_service.logout("invalid_token")

        assert result is False

    def test_get_user_by_id_success(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
        sample_user_doc: dict,
    ):
        mock_mongo_collection.find_one.return_value = sample_user_doc

        result = auth_service.get_user_by_id("user_123")

        assert result is not None
        assert result["user_id"] == "user_123"
        assert result["email"] == sample_user_doc["email"]

    def test_get_user_by_id_not_found(
        self,
        auth_service: AuthService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one.return_value = None

        result = auth_service.get_user_by_id("nonexistent")

        assert result is None
