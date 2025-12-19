"""
LLM Service - FastAPI Application

Modular monolith architecture with:
- MongoDB connection pool (shared/persistance)
- LangChain/LangGraph module (modules/langchain)
  - agents/: LangGraph agents
  - tools/: Custom tools
  - services/: Business logic
  - http_handlers/: FastAPI routes
- Web module (modules/web)
  - HTMX-based web interface
  - Authentication and chat
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

from config.settings import settings
from shared.persistance.mongo_db import mongo_pool
from modules.langchain.http_handlers.conversation import router as conversation_router
from modules.web import pages_router, auth_router, chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Manages MongoDB connection pool startup/shutdown.
    """
    # Startup
    print("🚀 Starting LLM Service...")
    
    try:
        mongo_pool.connect(settings.MONGO_URI)
        print(f"✅ MongoDB connected to {settings.MONGO_DB}")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise
    
    yield
    
    # Shutdown
    print("👋 Shutting down LLM Service...")
    mongo_pool.close()
    print("✅ MongoDB connection closed")


# Create FastAPI app
app = FastAPI(
    title="LLM Service",
    description="Back-end service for LLM conversations with memory persistence",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers from modules
app.include_router(conversation_router)

# Web module routes (HTMX interface)
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(chat_router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "service": "LLM Service",
        "version": "0.1.0",
        "status": "healthy",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test MongoDB connection
        mongo_pool.client.admin.command("ping")
        mongo_status = "connected"
    except Exception as e:
        mongo_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if mongo_status == "connected" else "degraded",
        "mongodb": mongo_status,
        "database": settings.MONGO_DB,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
    )