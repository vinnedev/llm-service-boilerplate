import pytest
from datetime import datetime, timezone
from unittest.mock import patch
import uuid

from shared.models.users_model import UsersModel
from shared.models.sessions_model import (
    SessionsModel,
    SessionCreate,
    SessionResponse,
    generate_session_id,
    utc_now,
)


pytestmark = pytest.mark.unit


class TestUsersModel:
    def test_create_user_with_required_fields(self):
        now = datetime.now(timezone.utc)
        user = UsersModel(
            user_id="user_123",
            name="John Doe",
            email="john@example.com",
            created_at=now,
            updated_at=now,
        )

        assert user.user_id == "user_123"
        assert user.name == "John Doe"
        assert user.email == "john@example.com"

    def test_email_normalization(self):
        now = datetime.now(timezone.utc)
        user = UsersModel(
            user_id="user_123",
            name="John Doe",
            email="  JOHN@EXAMPLE.COM  ",
            created_at=now,
            updated_at=now,
        )

        assert user.email == "john@example.com"

    def test_optional_google_fields(self):
        now = datetime.now(timezone.utc)
        user = UsersModel(
            user_id="user_123",
            name="John Doe",
            email="john@example.com",
            google_id="google_abc",
            given_name="John",
            family_name="Doe",
            picture="https://example.com/photo.jpg",
            created_at=now,
            updated_at=now,
        )

        assert user.google_id == "google_abc"
        assert user.given_name == "John"
        assert user.family_name == "Doe"
        assert user.picture == "https://example.com/photo.jpg"

    def test_invalid_email_raises_error(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValueError):
            UsersModel(
                user_id="user_123",
                name="John Doe",
                email="invalid-email",
                created_at=now,
                updated_at=now,
            )


class TestSessionsModel:
    def test_create_session_model(self, sample_session: SessionsModel):
        assert sample_session.session_id == "session_456"
        assert sample_session.thread_id == "session_456"
        assert sample_session.user_id == "user_123"
        assert sample_session.name == "Test Session"

    def test_to_document(self, sample_session: SessionsModel):
        doc = sample_session.to_document()

        assert doc["_id"] == sample_session.session_id
        assert doc["session_id"] == sample_session.session_id
        assert doc["thread_id"] == sample_session.thread_id
        assert doc["user_id"] == sample_session.user_id
        assert doc["name"] == sample_session.name
        assert "created_at" in doc
        assert "updated_at" in doc

    def test_from_document(self, sample_session_doc: dict):
        session = SessionsModel.from_document(sample_session_doc)

        assert session.session_id == sample_session_doc["session_id"]
        assert session.thread_id == sample_session_doc["thread_id"]
        assert session.user_id == sample_session_doc["user_id"]
        assert session.name == sample_session_doc["name"]

    def test_from_document_fallback_ids(self):
        doc = {
            "_id": "fallback_id",
            "user_id": "user_123",
            "name": "Test",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        session = SessionsModel.from_document(doc)

        assert session.session_id == "fallback_id"
        assert session.thread_id == "fallback_id"

    def test_touch_updates_timestamp(self, sample_session: SessionsModel):
        original_updated_at = sample_session.updated_at
        touched = sample_session.touch()

        assert touched.session_id == sample_session.session_id
        assert touched.updated_at >= original_updated_at


class TestSessionCreate:
    def test_create_with_name(self):
        create = SessionCreate(user_id="user_123", name="Custom Name")
        assert create.user_id == "user_123"
        assert create.name == "Custom Name"

    def test_create_without_name(self):
        create = SessionCreate(user_id="user_123")
        assert create.user_id == "user_123"
        assert create.name is None

    def test_to_session_generates_ids(self):
        create = SessionCreate(user_id="user_123", name="Test")
        session = create.to_session()

        assert session.session_id is not None
        assert session.thread_id == session.session_id
        assert session.user_id == "user_123"
        assert session.name == "Test"
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_to_session_generates_default_name(self):
        create = SessionCreate(user_id="user_123")
        session = create.to_session()

        assert "Conversa" in session.name


class TestSessionResponse:
    def test_session_response_fields(self, sample_session: SessionsModel):
        response = SessionResponse(
            session_id=sample_session.session_id,
            thread_id=sample_session.thread_id,
            user_id=sample_session.user_id,
            name=sample_session.name,
            created_at=sample_session.created_at,
            updated_at=sample_session.updated_at,
            is_new=True,
        )

        assert response.is_new is True
        assert response.session_id == sample_session.session_id


class TestUtilityFunctions:
    def test_generate_session_id_returns_uuid(self):
        session_id = generate_session_id()
        uuid.UUID(session_id)

    def test_generate_session_id_unique(self):
        ids = [generate_session_id() for _ in range(100)]
        assert len(set(ids)) == 100

    def test_utc_now_returns_utc(self):
        now = utc_now()
        assert now.tzinfo == timezone.utc
