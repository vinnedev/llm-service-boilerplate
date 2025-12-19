"""
Pages HTTP Handler - Serve HTML pages for web interface.
"""
from typing import Optional
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from shared.models.users_model import UsersModel
from shared.services.logger import get_logger
from shared.persistance.mongo_db import mongo_pool
from modules.web.services.auth_service import AuthService
from modules.langchain.services.session_service import SessionService
from modules.langchain.services.checkpointer import CheckpointerFactory
from modules.langchain.agents.conversation_agent import ConversationAgent


logger = get_logger(__name__)

router = APIRouter(prefix="/web", tags=["Web Pages"])

# Templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


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


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[UsersModel]:
    """Get current user from auth token cookie."""
    token = request.cookies.get("auth_token")
    if not token:
        return None
    return auth_service.get_user_by_token(token)


# --- Public Pages ---

@router.get("/", response_class=HTMLResponse)
async def home(request: Request, user: Optional[UsersModel] = Depends(get_current_user)):
    """Home page - redirect based on auth status."""
    if user:
        return RedirectResponse(url="/web/chat", status_code=302)
    return RedirectResponse(url="/web/login", status_code=302)


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user: Optional[UsersModel] = Depends(get_current_user)):
    """Login page."""
    if user:
        return RedirectResponse(url="/web/chat", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user: Optional[UsersModel] = Depends(get_current_user)):
    """Registration page."""
    if user:
        return RedirectResponse(url="/web/chat", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})


# --- Protected Pages ---

@router.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    session_id: Optional[str] = None,
    user: Optional[UsersModel] = Depends(get_current_user),
    session_service: SessionService = Depends(get_session_service),
    checkpointer_factory: CheckpointerFactory = Depends(get_checkpointer_factory),
):
    """Chat page - requires authentication."""
    if not user:
        return RedirectResponse(url="/web/login", status_code=302)
    
    logger.info(f"Loading chat page for user {user.user_id}")
    
    # Load user sessions
    sessions = session_service.list_user_sessions(user_id=user.user_id)
    logger.info(f"Found {len(sessions)} sessions for user")
    
    # Get current session if specified
    current_session = None
    messages = []
    
    if session_id:
        current_session = session_service.get_session(session_id)
        if current_session and current_session.user_id != user.user_id:
            current_session = None
        
        # Load message history from checkpointer
        if current_session:
            try:
                checkpointer = checkpointer_factory.create()
                agent = ConversationAgent(checkpointer)
                messages = agent.get_history(current_session.thread_id)
                logger.info(f"Loaded {len(messages)} messages for session {session_id}")
            except Exception as e:
                logger.error(f"Error loading message history: {e}")
    
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user": user,
        "sessions": sessions,
        "current_session": current_session,
        "current_session_id": session_id if current_session else None,
        "messages": messages,
    })
