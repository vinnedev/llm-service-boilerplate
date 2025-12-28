import pytest
from datetime import datetime, timezone

from shared.models.sessions_model import SessionCreate, SessionsModel
from modules.langchain.services.session_service import SessionService


pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestSessionServiceIntegration:
    @pytest.fixture
    def session_service(self, sessions_collection) -> SessionService:
        return SessionService(collection=sessions_collection)

    def test_create_and_get_session(self, session_service: SessionService):
        create_data = SessionCreate(user_id="integration_user", name="Integration Test")

        created = session_service.create_session(create_data)
        retrieved = session_service.get_session(created.session_id)

        assert retrieved is not None
        assert retrieved.session_id == created.session_id
        assert retrieved.user_id == "integration_user"
        assert retrieved.name == "Integration Test"
        assert retrieved.thread_id == created.session_id

    def test_create_session_generates_ids(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user")

        created = session_service.create_session(create_data)

        assert created.session_id is not None
        assert created.thread_id is not None
        assert created.session_id == created.thread_id
        assert created.is_new is True

    def test_create_session_default_name(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user")

        created = session_service.create_session(create_data)

        assert "Conversa" in created.name

    def test_get_session_not_found(self, session_service: SessionService):
        result = session_service.get_session("nonexistent_session_id")

        assert result is None

    def test_get_session_by_thread(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user", name="Thread Test")
        created = session_service.create_session(create_data)

        retrieved = session_service.get_session_by_thread(created.thread_id)

        assert retrieved is not None
        assert retrieved.thread_id == created.thread_id

    def test_list_user_sessions(self, session_service: SessionService):
        user_id = "multi_session_user"
        for i in range(3):
            session_service.create_session(
                SessionCreate(user_id=user_id, name=f"Session {i}")
            )

        sessions = session_service.list_user_sessions(user_id)

        assert len(sessions) == 3
        assert all(s.user_id == user_id for s in sessions)

    def test_list_user_sessions_sorted_by_updated_at(self, session_service: SessionService):
        user_id = "sorted_user"
        first = session_service.create_session(
            SessionCreate(user_id=user_id, name="First")
        )
        second = session_service.create_session(
            SessionCreate(user_id=user_id, name="Second")
        )

        session_service.touch_session(first.session_id)

        sessions = session_service.list_user_sessions(user_id)

        assert sessions[0].session_id == first.session_id

    def test_list_user_sessions_empty(self, session_service: SessionService):
        sessions = session_service.list_user_sessions("no_sessions_user")

        assert len(sessions) == 0

    def test_touch_session(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user", name="Touch Test")
        created = session_service.create_session(create_data)

        import time
        time.sleep(0.01)
        touched = session_service.touch_session(created.session_id)

        assert touched is not None
        assert touched.updated_at is not None
        assert touched.session_id == created.session_id

    def test_touch_session_not_found(self, session_service: SessionService):
        result = session_service.touch_session("nonexistent")

        assert result is None

    def test_update_session_name(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user", name="Original Name")
        created = session_service.create_session(create_data)

        updated = session_service.update_session_name(created.session_id, "Updated Name")

        assert updated is not None
        assert updated.name == "Updated Name"

    def test_update_session_name_not_found(self, session_service: SessionService):
        result = session_service.update_session_name("nonexistent", "New Name")

        assert result is None

    def test_delete_session(self, session_service: SessionService):
        create_data = SessionCreate(user_id="test_user", name="To Delete")
        created = session_service.create_session(create_data)

        deleted = session_service.delete_session(created.session_id)
        retrieved = session_service.get_session(created.session_id)

        assert deleted is True
        assert retrieved is None

    def test_delete_session_not_found(self, session_service: SessionService):
        result = session_service.delete_session("nonexistent")

        assert result is False

    def test_get_or_create_default_session_creates_new(self, session_service: SessionService):
        result = session_service.get_or_create_default_session(
            "new_user",
            session_name="Default Session"
        )

        assert result.is_new is True
        assert result.user_id == "new_user"

    def test_get_or_create_default_session_returns_existing(self, session_service: SessionService):
        user_id = "existing_user"
        first = session_service.create_session(
            SessionCreate(user_id=user_id, name="Existing")
        )

        result = session_service.get_or_create_default_session(user_id)

        assert result.is_new is False
        assert result.session_id == first.session_id

    def test_session_persistence_across_operations(self, session_service: SessionService):
        create_data = SessionCreate(user_id="persist_user", name="Persist Test")
        created = session_service.create_session(create_data)

        session_service.update_session_name(created.session_id, "Updated Persist")
        session_service.touch_session(created.session_id)
        retrieved = session_service.get_session(created.session_id)

        assert retrieved.name == "Updated Persist"
        assert retrieved.updated_at is not None
