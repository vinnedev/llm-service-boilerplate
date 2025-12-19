"""
Chat HTTP Handler - Web chat routes for HTMX interface.
"""
import json
import asyncio
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from shared.models.users_model import UsersModel
from shared.models.sessions_model import SessionCreate
from shared.services.logger import get_logger
from shared.persistance.mongo_db import mongo_pool
from modules.web.services.auth_service import AuthService
from modules.langchain.services.session_service import SessionService
from modules.langchain.services.checkpointer import CheckpointerFactory
from modules.langchain.agents.conversation_agent import ConversationAgent


logger = get_logger(__name__)

# SSE Keep-alive interval in seconds
SSE_KEEPALIVE_INTERVAL = 15

router = APIRouter(prefix="/web/chat", tags=["Web Chat"])


# --- Dependencies ---

def get_auth_service() -> AuthService:
    """Dependency: Get auth service instance."""
    return AuthService()


def get_session_service() -> SessionService:
    """Dependency: Get session service instance."""
    return SessionService()


def get_checkpointer_factory() -> CheckpointerFactory:
    """Dependency: Get checkpointer factory with MongoDB client."""
    return CheckpointerFactory(client=mongo_pool.client)


async def require_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> UsersModel:
    """Require authenticated user or raise 401."""
    token = request.cookies.get("auth_token")
    if not token:
        logger.warning("Unauthorized access attempt - no token")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = auth_service.get_user_by_token(token)
    if not user:
        logger.warning("Unauthorized access attempt - invalid token")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return user


# --- Session Routes (JSON API for frontend) ---

@router.post("/session")
async def create_session(
    request: Request,
    user: UsersModel = Depends(require_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Create a new chat session. Returns JSON."""
    logger.info(f"Creating new session for user {user.user_id}")
    
    # Create session with default name
    session_data = SessionCreate(
        user_id=user.user_id,
        name="Nova Conversa",
    )
    
    session = session_service.create_session(session_data)
    logger.info(f"Session created: {session.session_id}")
    
    return JSONResponse({
        "session_id": session.session_id,
        "name": session.name,
        "created_at": session.created_at.isoformat(),
    })


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    user: UsersModel = Depends(require_user),
    session_service: SessionService = Depends(get_session_service),
    checkpointer_factory: CheckpointerFactory = Depends(get_checkpointer_factory),
):
    """Delete a chat session and its conversation history."""
    logger.info(f"Deleting session {session_id} for user {user.user_id}")
    
    session = session_service.get_session(session_id)
    
    # Verify ownership
    if not session or session.user_id != user.user_id:
        logger.warning(f"Session {session_id} not found or unauthorized")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Delete checkpoint/conversation history
    try:
        checkpointer = checkpointer_factory.create()
        # Delete the thread from checkpointer (pass thread_id as string)
        checkpointer.delete_thread(session.thread_id)
        logger.info(f"Checkpoint for thread {session.thread_id} deleted")
    except Exception as e:
        logger.warning(f"Error deleting checkpoint: {e}")
    
    # Delete session
    session_service.delete_session(session_id)
    logger.info(f"Session {session_id} deleted")
    
    return JSONResponse({"success": True})


@router.patch("/session/{session_id}")
async def rename_session(
    session_id: str,
    request: Request,
    user: UsersModel = Depends(require_user),
    session_service: SessionService = Depends(get_session_service),
):
    """Rename a chat session."""
    logger.info(f"Renaming session {session_id} for user {user.user_id}")
    
    session = session_service.get_session(session_id)
    
    # Verify ownership
    if not session or session.user_id != user.user_id:
        logger.warning(f"Session {session_id} not found or unauthorized")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get new name from JSON body
    try:
        body = await request.json()
        new_name = body.get("name", "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not new_name:
        raise HTTPException(status_code=400, detail="Name is required")
    
    # Update session name
    updated_session = session_service.update_session_name(session_id, new_name)
    logger.info(f"Session {session_id} renamed to '{new_name}'")
    
    return JSONResponse({
        "success": True,
        "session_id": updated_session.session_id,
        "name": updated_session.name,
    })


@router.get("/session/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    user: UsersModel = Depends(require_user),
    session_service: SessionService = Depends(get_session_service),
    checkpointer_factory: CheckpointerFactory = Depends(get_checkpointer_factory),
):
    """Get messages for a session (for dynamic loading without page reload)."""
    logger.info(f"Getting messages for session {session_id}")
    
    session = session_service.get_session(session_id)
    
    # Verify ownership
    if not session or session.user_id != user.user_id:
        logger.warning(f"Session {session_id} not found or unauthorized")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get messages from checkpointer
    checkpointer = checkpointer_factory.create()
    agent = ConversationAgent(checkpointer)
    messages = agent.get_history(session.thread_id)
    
    return JSONResponse({
        "session_id": session.session_id,
        "name": session.name,
        "messages": messages,
    })


# --- Chat Message Routes ---

@router.post("/send/{session_id}")
async def send_message(
    session_id: str,
    request: Request,
    user: UsersModel = Depends(require_user),
    session_service: SessionService = Depends(get_session_service),
    checkpointer_factory: CheckpointerFactory = Depends(get_checkpointer_factory),
):
    """Send a message and stream the response via SSE."""
    logger.info(f"Message received for session {session_id}")
    
    session = session_service.get_session(session_id)
    
    # Verify ownership
    if not session or session.user_id != user.user_id:
        logger.warning(f"Session {session_id} not found or unauthorized")
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Get message from JSON body
    try:
        body = await request.json()
        message = body.get("message", "").strip()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    
    if not message:
        raise HTTPException(status_code=400, detail="Message is required")
    
    logger.info(f"Processing message for session {session_id}: {message[:50]}...")
    
    # Touch session to update timestamp
    session_service.touch_session(session_id)
    
    # Stream response with keep-alive
    async def generate():
        queue: asyncio.Queue = asyncio.Queue()
        done_event = asyncio.Event()
        
        async def stream_agent():
            """Stream agent response chunks to queue."""
            try:
                checkpointer = checkpointer_factory.create()
                agent = ConversationAgent(checkpointer)
                
                async for chunk in agent.stream(message, session.thread_id):
                    await queue.put({"chunk": chunk})
                
                # Signal completion
                await queue.put({"done": True})
                    
            except Exception as e:
                logger.error(f"Error streaming response: {e}")
                await queue.put({"error": str(e)})
            finally:
                done_event.set()
        
        async def keepalive():
            """Send periodic keep-alive comments."""
            while not done_event.is_set():
                try:
                    await asyncio.wait_for(
                        done_event.wait(),
                        timeout=SSE_KEEPALIVE_INTERVAL
                    )
                except asyncio.TimeoutError:
                    # Send keep-alive comment (SSE comment format)
                    await queue.put(None)  # None signals keep-alive
        
        # Start both tasks
        agent_task = asyncio.create_task(stream_agent())
        keepalive_task = asyncio.create_task(keepalive())
        
        try:
            while True:
                try:
                    # Wait for next item with timeout
                    item = await asyncio.wait_for(queue.get(), timeout=60)
                    
                    if item is None:
                        # Keep-alive comment
                        yield ": keepalive\n\n"
                    else:
                        # Data event
                        yield f"data: {json.dumps(item)}\n\n"
                        
                        if item.get("done") or item.get("error"):
                            break
                            
                except asyncio.TimeoutError:
                    # Safety timeout - send keepalive
                    yield ": keepalive\n\n"
                    if done_event.is_set():
                        break
        finally:
            # Clean up tasks
            keepalive_task.cancel()
            try:
                await keepalive_task
            except asyncio.CancelledError:
                pass
            await agent_task
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
