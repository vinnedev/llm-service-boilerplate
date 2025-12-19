"""
Session Service - Manages user chat sessions with MongoDB persistence.

Uses SessionsModel for data validation and persistence.
"""
from datetime import datetime, timezone
from typing import Optional

from pymongo.collection import Collection

from shared.persistance.mongo_db import mongo_pool
from shared.models.sessions_model import (
    SessionsModel,
    SessionCreate,
    SessionResponse,
    utc_now,
)
from shared.services.logger import get_logger
from config.settings import settings


logger = get_logger(__name__)


class SessionService:
    """
    Service for managing user chat sessions.
    
    - Each session has a unique session_id (UUID)
    - thread_id = session_id (used by LangGraph checkpointer)
    - A user can have multiple sessions
    """
    
    def __init__(self, collection: Optional[Collection] = None):
        """
        Initialize session service.
        
        Args:
            collection: MongoDB collection (injected for testing, otherwise uses pool)
        """
        self._collection = collection
    
    @property
    def collection(self) -> Collection:
        """Get sessions collection (lazy-loaded from pool if not injected)."""
        if self._collection is None:
            self._collection = mongo_pool.get_collection(
                settings.SESSIONS_COLLECTION,
                settings.MONGO_DB
            )
        return self._collection
    
    def create_session(
        self,
        data: SessionCreate,
    ) -> SessionResponse:
        """
        Create a new session for a user.
        
        Args:
            data: Session creation data
            
        Returns:
            SessionResponse with session details
        """
        logger.info(f"Creating session for user {data.user_id}")
        
        # Use model to create session with proper validation
        session = data.to_session()
        
        # Persist to MongoDB
        self.collection.insert_one(session.to_document())
        logger.info(f"Session created: {session.session_id}")
        
        return SessionResponse(
            session_id=session.session_id,
            thread_id=session.thread_id,
            user_id=session.user_id,
            name=session.name,
            created_at=session.created_at,
            updated_at=session.updated_at,
            is_new=True,
        )
    
    def get_session(self, session_id: str) -> Optional[SessionsModel]:
        """
        Get session by session_id.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            SessionsModel or None if not found
        """
        logger.debug(f"Getting session: {session_id}")
        doc = self.collection.find_one({"session_id": session_id})
        if doc:
            return SessionsModel.from_document(doc)
        return None
    
    def get_session_by_thread(self, thread_id: str) -> Optional[SessionsModel]:
        """
        Get session by thread_id.
        
        Args:
            thread_id: Thread identifier (same as session_id)
            
        Returns:
            SessionsModel or None if not found
        """
        doc = self.collection.find_one({"thread_id": thread_id})
        if doc:
            return SessionsModel.from_document(doc)
        return None
    
    def list_user_sessions(self, user_id: str) -> list[SessionsModel]:
        """
        List all sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of SessionsModel
        """
        docs = self.collection.find(
            {"user_id": user_id}
        ).sort("updated_at", -1)
        
        return [SessionsModel.from_document(doc) for doc in docs]
    
    def touch_session(self, session_id: str) -> Optional[SessionsModel]:
        """
        Update session's updated_at timestamp.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Updated SessionsModel or None if not found
        """
        now = utc_now()
        
        result = self.collection.find_one_and_update(
            {"session_id": session_id},
            {"$set": {"updated_at": now}},
            return_document=True,
        )
        
        if result:
            return SessionsModel.from_document(result)
        return None
    
    def update_session_name(
        self,
        session_id: str,
        name: str,
    ) -> Optional[SessionsModel]:
        """
        Update session name.
        
        Args:
            session_id: Session identifier
            name: New session name
            
        Returns:
            Updated SessionsModel or None if not found
        """
        now = utc_now()
        
        result = self.collection.find_one_and_update(
            {"session_id": session_id},
            {"$set": {"name": name, "updated_at": now}},
            return_document=True,
        )
        
        if result:
            return SessionsModel.from_document(result)
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if deleted, False if not found
        """
        result = self.collection.delete_one({"session_id": session_id})
        return result.deleted_count > 0
    
    def get_or_create_default_session(
        self,
        user_id: str,
        session_name: Optional[str] = None,
    ) -> SessionResponse:
        """
        Get most recent session for user or create new one.
        
        Useful for single-session flows where you want to continue
        the last conversation or start a new one.
        
        Args:
            user_id: User identifier
            session_name: Optional name for new session
            
        Returns:
            SessionResponse with session details
        """
        # Get most recent session
        sessions = self.list_user_sessions(user_id)
        
        if sessions:
            session = sessions[0]  # Most recent (sorted by updated_at desc)
            self.touch_session(session.session_id)
            
            return SessionResponse(
                session_id=session.session_id,
                thread_id=session.thread_id,
                user_id=session.user_id,
                name=session.name,
                created_at=session.created_at,
                updated_at=utc_now(),
                is_new=False,
            )
        
        # Create new session
        return self.create_session(SessionCreate(user_id=user_id, name=session_name))
