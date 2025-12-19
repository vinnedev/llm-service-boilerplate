"""
Sessions Model - Pydantic model for chat sessions.
"""
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid


def generate_session_id() -> str:
    """Generate a unique session ID (UUID)."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class SessionCreate(BaseModel):
    """Model for creating a new session."""
    user_id: str
    name: Optional[str] = None
    
    def to_session(self) -> "SessionsModel":
        """Convert to full session model with generated fields."""
        session_id = generate_session_id()
        now = utc_now()
        return SessionsModel(
            session_id=session_id,
            thread_id=session_id,  # thread_id = session_id
            user_id=self.user_id,
            name=self.name or f"Conversa {now.strftime('%d/%m/%Y %H:%M')}",
            created_at=now,
            updated_at=now,
        )


class SessionsModel(BaseModel):
    """
    Session model for MongoDB persistence.
    
    - session_id: Unique session identifier (UUID), also used as thread_id for checkpointer
    - thread_id: Same as session_id, used by LangGraph checkpointer
    - user_id: User who owns this session
    - name: Human-readable session name
    - created_at: Session creation timestamp
    - updated_at: Last activity timestamp
    """
    session_id: str = Field(description="Unique session ID (UUID)")
    thread_id: str = Field(description="Thread ID for LangGraph checkpointer (same as session_id)")
    user_id: str = Field(description="User ID who owns this session")
    name: str = Field(description="Session display name")
    created_at: datetime = Field(description="Creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
    
    def to_document(self) -> dict:
        """Convert to MongoDB document format."""
        return {
            "_id": self.session_id,
            "session_id": self.session_id,
            "thread_id": self.thread_id,
            "user_id": self.user_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
    
    @classmethod
    def from_document(cls, doc: dict) -> "SessionsModel":
        """Create model from MongoDB document."""
        return cls(
            session_id=doc.get("session_id") or str(doc.get("_id")),
            thread_id=doc.get("thread_id") or doc.get("session_id") or str(doc.get("_id")),
            user_id=doc["user_id"],
            name=doc.get("name", ""),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )
    
    def touch(self) -> "SessionsModel":
        """Return updated model with new updated_at timestamp."""
        return self.model_copy(update={"updated_at": utc_now()})


class SessionResponse(BaseModel):
    """Response model for session endpoints."""
    session_id: str
    thread_id: str
    user_id: str
    name: str
    created_at: datetime
    updated_at: datetime
    is_new: bool = False