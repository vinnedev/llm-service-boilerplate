"""
Checkpointer Factory - Creates MongoDB checkpointer instances.

No global state - uses dependency injection pattern.
"""
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from config.settings import settings


class CheckpointerFactory:
    """
    Factory for creating MongoDB checkpointer instances.
    
    Uses dependency injection - receives MongoDB client instead of
    managing global state.
    """
    
    def __init__(self, client: MongoClient):
        """
        Initialize factory with MongoDB client.
        
        Args:
            client: PyMongo client instance
        """
        self._client = client
        self._db_name = settings.MONGO_DB
        self._collection_name = settings.CHECKPOINT_COLLECTION
    
    def create(self) -> MongoDBSaver:
        """
        Create a new MongoDBSaver checkpointer.
        
        Returns:
            Configured MongoDBSaver instance
        """
        return MongoDBSaver(
            client=self._client,
            db_name=self._db_name,
            collection_name=self._collection_name,
        )


def create_checkpointer(client: MongoClient) -> MongoDBSaver:
    """
    Convenience function to create checkpointer.
    
    Args:
        client: PyMongo client instance
        
    Returns:
        Configured MongoDBSaver instance
    """
    factory = CheckpointerFactory(client)
    return factory.create()
