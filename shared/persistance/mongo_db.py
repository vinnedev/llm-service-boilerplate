"""
MongoDB Connection Pool - Singleton pattern for connection reuse.
"""
from pymongo import MongoClient
from pymongo.database import Database
from typing import Optional
import os


class MongoDBPool:
    """Singleton MongoDB connection pool."""
    
    _instance: Optional["MongoDBPool"] = None
    _client: Optional[MongoClient] = None
    
    def __new__(cls) -> "MongoDBPool":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def connect(self, uri: Optional[str] = None) -> MongoClient:
        """
        Initialize or return existing MongoDB client.
        Uses connection pooling by default (maxPoolSize=100).
        """
        if self._client is None:
            self._client = MongoClient(
                uri,
                maxPoolSize=100,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                connectTimeoutMS=5000,
                serverSelectionTimeoutMS=5000,
            )
            # Test connection
            self._client.admin.command("ping")
        return self._client
    
    def get_database(self, db_name: Optional[str] = None) -> Database:
        """Get database instance."""
        if self._client is None:
            self.connect()
        return self._client[db_name]
    
    def get_collection(self, collection_name: str, db_name: Optional[str] = None):
        """Get collection from database."""
        db = self.get_database(db_name)
        return db[collection_name]
    
    def close(self) -> None:
        """Close MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
    
    @property
    def client(self) -> Optional[MongoClient]:
        """Get raw client (connects if needed)."""
        if self._client is None:
            self.connect()
        return self._client


# Global singleton instance
mongo_pool = MongoDBPool()


def get_mongo_client() -> MongoClient:
    """FastAPI dependency: get MongoDB client."""
    return mongo_pool.client


def get_database(db_name: Optional[str] = None) -> Database:
    """FastAPI dependency: get database."""
    return mongo_pool.get_database(db_name)
