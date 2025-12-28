import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from shared.models.sessions_model import SessionsModel, SessionCreate, SessionResponse
from modules.langchain.services.session_service import SessionService
from tests.conftest import MockCursor, create_mock_find


pytestmark = pytest.mark.unit


class TestSessionService:
    @pytest.fixture
    def session_service(self, mock_mongo_collection: MagicMock) -> SessionService:
        return SessionService(collection=mock_mongo_collection)

    def test_create_session_success(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_create: SessionCreate,
    ):
        result = session_service.create_session(sample_session_create)

        assert isinstance(result, SessionResponse)
        assert result.user_id == sample_session_create.user_id
        assert result.is_new is True
        mock_mongo_collection.insert_one.assert_called_once()

    def test_create_session_uses_custom_name(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        create = SessionCreate(user_id="user_123", name="My Custom Chat")
        result = session_service.create_session(create)

        assert result.name == "My Custom Chat"

    def test_get_session_found(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        mock_mongo_collection.find_one.return_value = sample_session_doc

        result = session_service.get_session("session_456")

        assert result is not None
        assert isinstance(result, SessionsModel)
        assert result.session_id == "session_456"
        mock_mongo_collection.find_one.assert_called_once_with({"session_id": "session_456"})

    def test_get_session_not_found(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one.return_value = None

        result = session_service.get_session("nonexistent")

        assert result is None

    def test_get_session_by_thread(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        mock_mongo_collection.find_one.return_value = sample_session_doc

        result = session_service.get_session_by_thread("session_456")

        assert result is not None
        mock_mongo_collection.find_one.assert_called_once_with({"thread_id": "session_456"})

    def test_list_user_sessions(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        mock_mongo_collection.find = create_mock_find([sample_session_doc])

        result = session_service.list_user_sessions("user_123")

        assert len(result) == 1
        assert result[0].session_id == "session_456"

    def test_list_user_sessions_empty(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find = create_mock_find([])

        result = session_service.list_user_sessions("user_with_no_sessions")

        assert len(result) == 0

    def test_touch_session_success(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        mock_mongo_collection.find_one_and_update.return_value = sample_session_doc

        result = session_service.touch_session("session_456")

        assert result is not None
        mock_mongo_collection.find_one_and_update.assert_called_once()

    def test_touch_session_not_found(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one_and_update.return_value = None

        result = session_service.touch_session("nonexistent")

        assert result is None

    def test_update_session_name_success(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        updated_doc = {**sample_session_doc, "name": "New Name"}
        mock_mongo_collection.find_one_and_update.return_value = updated_doc

        result = session_service.update_session_name("session_456", "New Name")

        assert result is not None
        assert result.name == "New Name"

    def test_update_session_name_not_found(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find_one_and_update.return_value = None

        result = session_service.update_session_name("nonexistent", "New Name")

        assert result is None

    def test_delete_session_success(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.delete_one.return_value = MagicMock(deleted_count=1)

        result = session_service.delete_session("session_456")

        assert result is True
        mock_mongo_collection.delete_one.assert_called_once_with({"session_id": "session_456"})

    def test_delete_session_not_found(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.delete_one.return_value = MagicMock(deleted_count=0)

        result = session_service.delete_session("nonexistent")

        assert result is False

    def test_get_or_create_default_session_returns_existing(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
        sample_session_doc: dict,
    ):
        mock_mongo_collection.find = create_mock_find([sample_session_doc])
        mock_mongo_collection.find_one_and_update.return_value = sample_session_doc

        result = session_service.get_or_create_default_session("user_123")

        assert result.is_new is False
        assert result.session_id == "session_456"

    def test_get_or_create_default_session_creates_new(
        self,
        session_service: SessionService,
        mock_mongo_collection: MagicMock,
    ):
        mock_mongo_collection.find = create_mock_find([])

        result = session_service.get_or_create_default_session("user_123", "New Chat")

        assert result.is_new is True
        mock_mongo_collection.insert_one.assert_called_once()
