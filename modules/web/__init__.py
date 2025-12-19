"""
Web Module - HTMX-based web interface for chat application.

Structure:
- services/: Business logic (auth, user management)
- http_handlers/: FastAPI routes for web pages
- templates/: Jinja2 HTML templates
- static/: CSS, JS files
"""
from modules.web.http_handlers.pages import router as pages_router
from modules.web.http_handlers.auth import router as auth_router
from modules.web.http_handlers.chat import router as chat_router

__all__ = [
    "pages_router",
    "auth_router", 
    "chat_router",
]
