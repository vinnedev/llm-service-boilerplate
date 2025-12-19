"""
Conversation Agent - LangGraph agent for chat conversations.

No global state - uses dependency injection pattern.
"""
from typing import AsyncGenerator, Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
from langchain.agents import create_agent
from langgraph.checkpoint.mongodb import MongoDBSaver

from config.settings import settings
from shared.services.logger import get_logger


logger = get_logger(__name__)


class ConversationAgent:
    """
    Conversation agent with streaming support.
    
    Uses dependency injection - receives checkpointer instead of
    managing global state.
    """
    
    def __init__(self, checkpointer: MongoDBSaver):
        """
        Initialize agent with checkpointer.
        
        Args:
            checkpointer: MongoDB checkpointer for state persistence
        """
        self._checkpointer = checkpointer
        self._agent = self._create_agent()
        logger.debug("ConversationAgent initialized")
    
    def _create_agent(self) -> Any:
        """Create the LangGraph agent."""
        logger.debug(f"Creating agent with model {settings.OPENAI_MODEL}")
        model = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
            streaming=True,
        )
        
        return create_agent(
            model,
            tools=[],  # Add tools from tools/ folder as needed
            checkpointer=self._checkpointer,
        )
    
    async def stream(
        self,
        message: str,
        thread_id: str,
    ) -> AsyncGenerator[str, None]:
        """
        Stream conversation response.
        
        Args:
            message: User message
            thread_id: Session/thread identifier for checkpointer
            
        Yields:
            Chunks of AI response text
        """
        logger.info(f"Streaming response for thread {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        input_messages = {"messages": [HumanMessage(content=message)]}
        
        async for event in self._agent.astream_events(input_messages, config, version="v2"):
            kind = event.get("event")
            
            if kind == "on_chat_model_stream":
                content = event.get("data", {}).get("chunk", {})
                if hasattr(content, "content") and content.content:
                    yield content.content
        
        logger.debug(f"Streaming complete for thread {thread_id}")
    
    async def invoke(
        self,
        message: str,
        thread_id: str,
    ) -> str:
        """
        Invoke conversation and return complete response.
        
        Args:
            message: User message
            thread_id: Session/thread identifier for checkpointer
            
        Returns:
            Complete AI response text
        """
        logger.info(f"Invoking agent for thread {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        result = await self._agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config
        )
        
        messages = result.get("messages", [])
        if messages:
            last_message = messages[-1]
            if isinstance(last_message, AIMessage):
                logger.debug(f"Response received for thread {thread_id}")
                return last_message.content
            return str(last_message.content)
        
        return ""
    
    def get_history(self, thread_id: str) -> list[dict]:
        """
        Get conversation history for a thread.
        
        Args:
            thread_id: Session/thread identifier
            
        Returns:
            List of message dicts with role and content
        """
        logger.debug(f"Getting history for thread {thread_id}")
        config = {"configurable": {"thread_id": thread_id}}
        
        try:
            checkpoint_tuple = self._checkpointer.get_tuple(config)
            if checkpoint_tuple and checkpoint_tuple.checkpoint:
                messages = checkpoint_tuple.checkpoint.get("channel_values", {}).get("messages", [])
                logger.debug(f"Found {len(messages)} messages in history")
                return [
                    {
                        "role": "user" if isinstance(msg, HumanMessage) else "assistant",
                        "content": msg.content,
                    }
                    for msg in messages
                ]
        except Exception as e:
            logger.error(f"Error getting history: {e}")
        
        return []
