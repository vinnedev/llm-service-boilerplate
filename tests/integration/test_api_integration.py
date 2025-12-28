import pytest
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from modules.langchain.services.session_service import SessionService
from shared.models.sessions_model import SessionCreate


pytestmark = [pytest.mark.integration, pytest.mark.slow]


@pytest.fixture
def test_app():
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


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, test_app: FastAPI):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"


class TestSessionEndpoints:
    @pytest.mark.asyncio
    async def test_create_session(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/conversation/session",
                    json={"user_id": "test_user", "name": "API Test Session"}
                )

                assert response.status_code == 200
                data = response.json()
                assert data["user_id"] == "test_user"
                assert data["name"] == "API Test Session"
                assert "session_id" in data
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_create_session_missing_user_id(self, test_app: FastAPI):
        transport = ASGITransport(app=test_app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/conversation/session",
                json={"name": "No User Session"}
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_session(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        created = service.create_session(
            SessionCreate(user_id="test_user", name="Get Test")
        )

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(f"/conversation/session/{created.session_id}")

                assert response.status_code == 200
                data = response.json()
                assert data["session_id"] == created.session_id
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/conversation/session/nonexistent")
                assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_list_user_sessions(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        for i in range(3):
            service.create_session(
                SessionCreate(user_id="list_user", name=f"Session {i}")
            )

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/conversation/sessions/user/list_user")

                assert response.status_code == 200
                data = response.json()
                assert len(data["sessions"]) == 3
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_session(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        created = service.create_session(
            SessionCreate(user_id="test_user", name="To Delete")
        )

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(f"/conversation/session/{created.session_id}")

                assert response.status_code == 200
                assert service.get_session(created.session_id) is None
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete("/conversation/session/nonexistent")
                assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()


class TestConversationEndpoint:
    @pytest.mark.asyncio
    async def test_conversation_empty_message(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/conversation",
                    json={"user_id": "test_user", "message": "   ", "stream": False}
                )
                assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_conversation_empty_user_id(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/conversation",
                    json={"user_id": "   ", "message": "Hello", "stream": False}
                )
                assert response.status_code == 400
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_conversation_session_not_found(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import get_session_service

        service = SessionService(collection=sessions_collection)
        test_app.dependency_overrides[get_session_service] = lambda: service

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/conversation",
                    json={
                        "session_id": "nonexistent",
                        "user_id": "test_user",
                        "message": "Hello",
                        "stream": False
                    }
                )
                assert response.status_code == 404
        finally:
            test_app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_conversation_non_streaming(self, test_app: FastAPI, sessions_collection):
        from modules.langchain.http_handlers.conversation import (
            get_session_service,
            get_conversation_agent,
        )

        service = SessionService(collection=sessions_collection)
        mock_agent = MagicMock()
        mock_agent.invoke = AsyncMock(return_value="AI Response")

        test_app.dependency_overrides[get_session_service] = lambda: service
        test_app.dependency_overrides[get_conversation_agent] = lambda: mock_agent

        try:
            transport = ASGITransport(app=test_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
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
        finally:
            test_app.dependency_overrides.clear()
