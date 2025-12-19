"""
Conversation HTTP Handler - SSE streaming endpoint for LLM conversations.
"""
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from modules.langchain.agents.conversation_agent import ConversationAgent
from modules.langchain.services.session_service import SessionService
from modules.langchain.services.checkpointer import create_checkpointer
from shared.persistance.mongo_db import mongo_pool


router = APIRouter(prefix="/conversation", tags=["Conversation"])


# --- Dependency Injection ---

def get_session_service() -> SessionService:
    """Dependency: Get session service instance."""
    return SessionService()


def get_conversation_agent() -> ConversationAgent:
    """Dependency: Get conversation agent instance."""
    checkpointer = create_checkpointer(mongo_pool.client)
    return ConversationAgent(checkpointer)


# --- Request/Response Models ---

class ConversationRequest(BaseModel):
    """Request body for conversation endpoint."""
    session_id: Optional[str] = None  # If None, creates new session
    user_id: str
    message: str
    session_name: Optional[str] = None
    stream: bool = True


class ConversationResponse(BaseModel):
    """Response body for non-streaming conversation."""
    session_id: str
    thread_id: str
    user_id: str
    message: str
    response: str


class SessionCreateRequest(BaseModel):
    """Request body for creating a new session."""
    user_id: str
    name: Optional[str] = None


# --- SSE Generator ---

async def event_generator(
    agent: ConversationAgent,
    session_id: str,
    thread_id: str,
    user_id: str,
    message: str,
):
    """Generate SSE events for streaming response."""
    try:
        # Send session info first
        yield {
            "event": "session",
            "data": json.dumps({
                "session_id": session_id,
                "thread_id": thread_id,
                "user_id": user_id,
            })
        }
        
        # Stream the response chunks
        full_response = ""
        async for chunk in agent.stream(thread_id, message):
            full_response += chunk
            yield {
                "event": "message",
                "data": json.dumps({"chunk": chunk})
            }
        
        # Send completion event
        yield {
            "event": "done",
            "data": json.dumps({
                "full_response": full_response,
                "session_id": session_id,
                "thread_id": thread_id,
            })
        }
        
    except Exception as e:
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)})
        }


# --- Routes ---

@router.post("")
async def conversation(
    request: ConversationRequest,
    session_service: SessionService = Depends(get_session_service),
    agent: ConversationAgent = Depends(get_conversation_agent),
):
    """
    Conversation endpoint with LLM.
    
    Supports both streaming (SSE) and non-streaming responses.
    
    - **session_id**: Optional session ID. If not provided, creates new session.
    - **user_id**: User identifier (required for creating new sessions)
    - **message**: User message to send to LLM
    - **session_name**: Optional custom session name (for new sessions)
    - **stream**: If true, returns SSE stream. If false, returns complete response.
    
    ## SSE Events (when stream=true):
    - `session`: Session info with session_id and thread_id
    - `message`: Chunk of AI response
    - `done`: Completion event with full response
    - `error`: Error event if something fails
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    if not request.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")
    
    # Get existing session or create new one
    if request.session_id:
        session = session_service.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Touch session to update timestamp
        session_service.touch_session(session.session_id)
        
        session_id = session.session_id
        thread_id = session.thread_id
    else:
        # Create new session
        session_response = session_service.create_session(
            user_id=request.user_id,
            name=request.session_name,
        )
        session_id = session_response.session_id
        thread_id = session_response.thread_id
    
    if request.stream:
        return EventSourceResponse(
            event_generator(
                agent,
                session_id,
                thread_id,
                request.user_id,
                request.message,
            ),
            media_type="text/event-stream",
        )
    else:
        response = await agent.invoke(thread_id, request.message)
        
        return ConversationResponse(
            session_id=session_id,
            thread_id=thread_id,
            user_id=request.user_id,
            message=request.message,
            response=response,
        )


@router.post("/session")
async def create_session(
    request: SessionCreateRequest,
    session_service: SessionService = Depends(get_session_service),
):
    """Create a new chat session."""
    if not request.user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")
    
    session = session_service.create_session(
        user_id=request.user_id,
        name=request.name,
    )
    
    return session


@router.get("/session/{session_id}")
async def get_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Get session info by session_id."""
    session = session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.get("/sessions/user/{user_id}")
async def list_user_sessions(
    user_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    """List all sessions for a user."""
    sessions = session_service.list_user_sessions(user_id)
    return {"sessions": [s.model_dump() for s in sessions]}


@router.patch("/session/{session_id}")
async def update_session(
    session_id: str,
    name: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Update session name."""
    session = session_service.update_session_name(session_id, name)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
):
    """Delete a session."""
    deleted = session_service.delete_session(session_id)
    
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"message": "Session deleted", "session_id": session_id}


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    session_service: SessionService = Depends(get_session_service),
    agent: ConversationAgent = Depends(get_conversation_agent),
):
    """Get conversation history for a session."""
    session = session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    history = agent.get_history(session.thread_id)
    
    return {
        "session_id": session_id,
        "thread_id": session.thread_id,
        "messages": history,
    }
