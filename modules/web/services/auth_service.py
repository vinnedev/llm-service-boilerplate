"""
Auth Service - Simple authentication for web interface.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional
import hashlib
import secrets

from pymongo.collection import Collection

from shared.persistance.mongo_db import mongo_pool
from shared.models.users_model import UsersModel
from shared.services.logger import get_logger
from config.settings import settings


logger = get_logger(__name__)


class AuthService:
    """
    Simple authentication service.
    
    For demo purposes - in production use proper OAuth/JWT.
    """
    
    def __init__(self, collection: Optional[Collection] = None):
        self._collection = collection
        self._sessions_collection = None
    
    @property
    def collection(self) -> Collection:
        """Get users collection."""
        if self._collection is None:
            self._collection = mongo_pool.get_collection("users", settings.MONGO_DB)
        return self._collection
    
    @property
    def sessions_collection(self) -> Collection:
        """Get auth sessions collection (for login tokens)."""
        if self._sessions_collection is None:
            self._sessions_collection = mongo_pool.get_collection("auth_sessions", settings.MONGO_DB)
        return self._sessions_collection
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register(
        self,
        name: str,
        email: str,
        password: str,
    ) -> Optional[dict]:
        """
        Register a new user.
        
        Returns user dict or None if email exists.
        """
        logger.info(f"Registering new user: {email}")
        
        # Check if email exists
        if self.collection.find_one({"email": email.lower().strip()}):
            logger.warning(f"Email already exists: {email}")
            return None
        
        now = datetime.now(timezone.utc)
        user_id = secrets.token_hex(12)
        
        user_doc = {
            "_id": user_id,
            "user_id": user_id,
            "name": name.strip(),
            "email": email.lower().strip(),
            "password": self._hash_password(password),
            "created_at": now,
            "updated_at": now,
        }
        
        self.collection.insert_one(user_doc)
        logger.info(f"User registered: {user_id}")
        
        return {
            "user_id": user_id,
            "name": name,
            "email": email.lower().strip(),
        }
    
    def login(self, email: str, password: str) -> Optional[str]:
        """
        Login user and return session token.
        
        Returns session token or None if invalid credentials.
        """
        logger.info(f"Login attempt for: {email}")
        user = self.collection.find_one({"email": email.lower().strip()})
        
        if not user:
            logger.warning(f"Login failed - user not found: {email}")
            return None
        
        if user.get("password") != self._hash_password(password):
            logger.warning(f"Login failed - wrong password: {email}")
            return None
        
        # Create session token
        token = secrets.token_urlsafe(32)
        logger.info(f"Login successful: {email}")
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        self.sessions_collection.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "created_at": datetime.now(timezone.utc),
            "expires_at": expires_at,
        })
        
        return token
    
    def get_user_by_token(self, token: str) -> Optional[UsersModel]:
        """Get user from session token."""
        session = self.sessions_collection.find_one({
            "token": token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not session:
            return None
        
        user = self.collection.find_one({"user_id": session["user_id"]})
        
        if not user:
            return None
        
        return UsersModel(
            user_id=user["user_id"],
            name=user["name"],
            email=user["email"],
            created_at=user.get("created_at", datetime.now(timezone.utc)),
            updated_at=user.get("updated_at", datetime.now(timezone.utc)),
        )
    
    def logout(self, token: str) -> bool:
        """Logout user by deleting session."""
        result = self.sessions_collection.delete_one({"token": token})
        return result.deleted_count > 0
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        user = self.collection.find_one({"user_id": user_id})
        
        if not user:
            return None
        
        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "email": user["email"],
        }
