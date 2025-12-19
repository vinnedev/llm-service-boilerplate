"""
Auth HTTP Handler - Authentication routes for web interface.
"""
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from modules.web.services.auth_service import AuthService


router = APIRouter(prefix="/web/auth", tags=["Web Auth"])

# Templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))


# --- Dependencies ---

def get_auth_service() -> AuthService:
    """Dependency: Get auth service instance."""
    return AuthService()


# --- Routes ---

@router.post("/register")
async def register(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle registration form submission."""
    # Validate passwords match
    if password != password_confirm:
        return HTMLResponse("""
            <div class="bg-red-50 border-l-4 border-red-400 p-4 rounded">
                <p class="text-sm text-red-700">As senhas não coincidem.</p>
            </div>
        """)
    
    # Validate password length
    if len(password) < 6:
        return HTMLResponse("""
            <div class="bg-red-50 border-l-4 border-red-400 p-4 rounded">
                <p class="text-sm text-red-700">A senha deve ter pelo menos 6 caracteres.</p>
            </div>
        """)
    
    # Try to register
    user = auth_service.register(name, email, password)
    
    if not user:
        return HTMLResponse("""
            <div class="bg-red-50 border-l-4 border-red-400 p-4 rounded">
                <p class="text-sm text-red-700">Este email já está cadastrado.</p>
            </div>
        """)
    
    # Success - redirect to login
    return HTMLResponse("""
        <div class="bg-green-50 border-l-4 border-green-400 p-4 rounded">
            <p class="text-sm text-green-700">Conta criada com sucesso! Redirecionando...</p>
        </div>
        <script>setTimeout(() => window.location.href = '/web/login', 1500);</script>
    """)


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle login form submission."""
    token = auth_service.login(email, password)
    
    if not token:
        return HTMLResponse("""
            <div class="bg-red-50 border-l-4 border-red-400 p-4 rounded flex">
                <svg class="h-5 w-5 text-red-400 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
                </svg>
                <p class="text-sm text-red-700">Email ou senha incorretos.</p>
            </div>
        """)
    
    # Success - set cookie and redirect
    response = HTMLResponse("""
        <script>window.location.href = '/web/chat';</script>
    """)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        max_age=7 * 24 * 60 * 60,  # 7 days
        samesite="lax"
    )
    return response


@router.get("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
):
    """Handle logout."""
    token = request.cookies.get("auth_token")
    
    if token:
        auth_service.logout(token)
    
    response = RedirectResponse(url="/web/login", status_code=302)
    response.delete_cookie("auth_token")
    return response
