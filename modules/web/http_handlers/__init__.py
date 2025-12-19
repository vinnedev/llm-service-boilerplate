"""
Web HTTP Handlers Package.
"""
from .auth import router as auth_router
from .pages import router as pages_router
from .chat import router as chat_router

__all__ = ["auth_router", "pages_router", "chat_router"]
