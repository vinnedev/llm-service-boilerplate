import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from modules.langchain.agents.conversation_agent import ConversationAgent
from modules.langchain.services.checkpointer import CheckpointerFactory, create_checkpointer


pytestmark = pytest.mark.unit


class TestConversationAgent:
    @pytest.fixture
    def agent(self, mock_checkpointer: MagicMock) -> ConversationAgent:
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_agent = MagicMock()
                mock_create.return_value = mock_agent
                return ConversationAgent(mock_checkpointer)

    def test_init_creates_agent(self, mock_checkpointer: MagicMock):
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI") as mock_chat:
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_create.return_value = MagicMock()

                agent = ConversationAgent(mock_checkpointer)

                mock_chat.assert_called_once()
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self, mock_checkpointer: MagicMock):
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_agent = MagicMock()
                mock_chunk = MagicMock()
                mock_chunk.content = "Hello "

                async def mock_events(*args, **kwargs):
                    yield {"event": "on_chat_model_stream", "data": {"chunk": mock_chunk}}
                    mock_chunk.content = "World"
                    yield {"event": "on_chat_model_stream", "data": {"chunk": mock_chunk}}

                mock_agent.astream_events = mock_events
                mock_create.return_value = mock_agent

                agent = ConversationAgent(mock_checkpointer)
                chunks = []
                async for chunk in agent.stream("test message", "thread_123"):
                    chunks.append(chunk)

                assert len(chunks) == 2
                assert "Hello" in chunks[0]
                assert "World" in chunks[1]

    @pytest.mark.asyncio
    async def test_stream_filters_non_stream_events(self, mock_checkpointer: MagicMock):
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_agent = MagicMock()

                async def mock_events(*args, **kwargs):
                    yield {"event": "on_tool_start", "data": {}}
                    yield {"event": "on_chain_start", "data": {}}

                mock_agent.astream_events = mock_events
                mock_create.return_value = mock_agent

                agent = ConversationAgent(mock_checkpointer)
                chunks = []
                async for chunk in agent.stream("test", "thread_123"):
                    chunks.append(chunk)

                assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_invoke_returns_response(self, mock_checkpointer: MagicMock):
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_agent = MagicMock()
                mock_ai_message = AIMessage(content="AI Response")
                mock_agent.ainvoke = AsyncMock(return_value={"messages": [mock_ai_message]})
                mock_create.return_value = mock_agent

                agent = ConversationAgent(mock_checkpointer)
                result = await agent.invoke("test message", "thread_123")

                assert result == "AI Response"

    @pytest.mark.asyncio
    async def test_invoke_returns_empty_on_no_messages(self, mock_checkpointer: MagicMock):
        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_agent = MagicMock()
                mock_agent.ainvoke = AsyncMock(return_value={"messages": []})
                mock_create.return_value = mock_agent

                agent = ConversationAgent(mock_checkpointer)
                result = await agent.invoke("test", "thread_123")

                assert result == ""

    def test_get_history_returns_messages(self, mock_checkpointer: MagicMock):
        mock_checkpoint = MagicMock()
        mock_checkpoint.checkpoint = {
            "channel_values": {
                "messages": [
                    HumanMessage(content="Hello"),
                    AIMessage(content="Hi there!"),
                ]
            }
        }
        mock_checkpointer.get_tuple.return_value = mock_checkpoint

        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_create.return_value = MagicMock()
                agent = ConversationAgent(mock_checkpointer)

                history = agent.get_history("thread_123")

                assert len(history) == 2
                assert history[0]["role"] == "user"
                assert history[0]["content"] == "Hello"
                assert history[1]["role"] == "assistant"
                assert history[1]["content"] == "Hi there!"

    def test_get_history_returns_empty_on_no_checkpoint(self, mock_checkpointer: MagicMock):
        mock_checkpointer.get_tuple.return_value = None

        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_create.return_value = MagicMock()
                agent = ConversationAgent(mock_checkpointer)

                history = agent.get_history("thread_123")

                assert history == []

    def test_get_history_handles_exceptions(self, mock_checkpointer: MagicMock):
        mock_checkpointer.get_tuple.side_effect = Exception("DB Error")

        with patch("modules.langchain.agents.conversation_agent.ChatOpenAI"):
            with patch("modules.langchain.agents.conversation_agent.create_agent") as mock_create:
                mock_create.return_value = MagicMock()
                agent = ConversationAgent(mock_checkpointer)

                history = agent.get_history("thread_123")

                assert history == []


class TestCheckpointerFactory:
    def test_create_returns_mongodb_saver(self, mock_mongo_client: MagicMock):
        with patch("modules.langchain.services.checkpointer.MongoDBSaver") as mock_saver:
            factory = CheckpointerFactory(mock_mongo_client)
            factory.create()

            mock_saver.assert_called_once()

    def test_create_checkpointer_convenience_function(self, mock_mongo_client: MagicMock):
        with patch("modules.langchain.services.checkpointer.MongoDBSaver") as mock_saver:
            create_checkpointer(mock_mongo_client)

            mock_saver.assert_called_once()
