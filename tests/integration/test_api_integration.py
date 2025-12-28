import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.langchain.services.session_service import SessionService
from modules.web.services.auth_service import AuthService
from shared.models.sessions_model import SessionCreate


pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def test_app(sessions_collection):
    app = FastAPI(title="Test LLM Service")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from modules.langchain.http_handlers.conversation import router as conversation_router
    app.include_router(conversation_router)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
async def async_client(test_app):
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, async_client: AsyncClient):
        response = await async_client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSessionEndpoints:
    @pytest.fixture
    def session_service(self, sessions_collection) -> SessionService:
        return SessionService(collection=sessions_collection)

    @pytest.mark.asyncio
    async def test_create_session(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.post(
                "/conversation/session",
                json={"user_id": "test_user", "name": "API Test Session"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == "test_user"
            assert data["name"] == "API Test Session"
            assert "session_id" in data

    @pytest.mark.asyncio
    async def test_create_session_missing_user_id(self, async_client: AsyncClient):
        response = await async_client.post(
            "/conversation/session",
            json={"name": "No User Session"}
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_session(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        service = SessionService(collection=sessions_collection)
        created = service.create_session(
            SessionCreate(user_id="test_user", name="Get Test")
        )

        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            mock_get_service.return_value = service

            response = await async_client.get(
                f"/conversation/session/{created.session_id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == created.session_id

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.get("/conversation/session/nonexistent")

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_user_sessions(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        service = SessionService(collection=sessions_collection)
        for i in range(3):
            service.create_session(
                SessionCreate(user_id="list_user", name=f"Session {i}")
            )

        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            mock_get_service.return_value = service

            response = await async_client.get("/conversation/sessions/user/list_user")

            assert response.status_code == 200
            data = response.json()
            assert len(data["sessions"]) == 3

    @pytest.mark.asyncio
    async def test_delete_session(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        service = SessionService(collection=sessions_collection)
        created = service.create_session(
            SessionCreate(user_id="test_user", name="To Delete")
        )

        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            mock_get_service.return_value = service

            response = await async_client.delete(
                f"/conversation/session/{created.session_id}"
            )

            assert response.status_code == 200
            assert service.get_session(created.session_id) is None

    @pytest.mark.asyncio
    async def test_delete_session_not_found(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.delete("/conversation/session/nonexistent")

            assert response.status_code == 404


class TestConversationEndpoint:
    @pytest.mark.asyncio
    async def test_conversation_empty_message(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.post(
                "/conversation",
                json={
                    "user_id": "test_user",
                    "message": "   ",
                    "stream": False
                }
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_conversation_empty_user_id(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.post(
                "/conversation",
                json={
                    "user_id": "   ",
                    "message": "Hello",
                    "stream": False
                }
            )

            assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_conversation_session_not_found(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            service = SessionService(collection=sessions_collection)
            mock_get_service.return_value = service

            response = await async_client.post(
                "/conversation",
                json={
                    "session_id": "nonexistent",
                    "user_id": "test_user",
                    "message": "Hello",
                    "stream": False
                }
            )

            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_conversation_non_streaming(
        self,
        async_client: AsyncClient,
        sessions_collection,
    ):
        service = SessionService(collection=sessions_collection)

        with patch(
            "modules.langchain.http_handlers.conversation.get_session_service"
        ) as mock_get_service:
            mock_get_service.return_value = service

            with patch(
                "modules.langchain.http_handlers.conversation.get_conversation_agent"
            ) as mock_get_agent:
                mock_agent = MagicMock()
                mock_agent.invoke = AsyncMock(return_value="AI Response")
                mock_get_agent.return_value = mock_agent

                response = await async_client.post(
                    "/conversation",
                    json={
                        "user_id": "test_user",
                        "message": "Hello AI",
                        "stream": False
                    }
                )

                assert response.status_code == 200
                data = response.json()
                assert data["response"] == "AI Response"
                assert "session_id" in data
