import pytest
from unittest.mock import MagicMock, patch


pytestmark = pytest.mark.unit


class TestMongoDBPool:
    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        from shared.persistance.mongo_db import MongoDBPool
        MongoDBPool._instance = None
        MongoDBPool._client = None
        yield
        MongoDBPool._instance = None
        MongoDBPool._client = None

    def test_singleton_pattern(self):
        from shared.persistance.mongo_db import MongoDBPool
        pool1 = MongoDBPool()
        pool2 = MongoDBPool()

        assert pool1 is pool2

    def test_connect_creates_client(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            client = pool.connect("mongodb://localhost:27017")

            mock_client_class.assert_called_once()
            assert client is mock_client

    def test_connect_reuses_existing_client(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            pool.connect("mongodb://localhost:27017")
            pool.connect("mongodb://localhost:27017")

            assert mock_client_class.call_count == 1

    def test_get_database(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_db = MagicMock()
            mock_client.__getitem__.return_value = mock_db
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            pool.connect("mongodb://localhost:27017")
            db = pool.get_database("test_db")

            mock_client.__getitem__.assert_called_with("test_db")
            assert db is mock_db

    def test_get_collection(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_db.__getitem__.return_value = mock_collection
            mock_client.__getitem__.return_value = mock_db
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            pool.connect("mongodb://localhost:27017")
            collection = pool.get_collection("test_collection", "test_db")

            mock_db.__getitem__.assert_called_with("test_collection")
            assert collection is mock_collection

    def test_close(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            pool.connect("mongodb://localhost:27017")
            pool.close()

            mock_client.close.assert_called_once()
            assert pool._client is None

    def test_close_when_not_connected(self):
        from shared.persistance.mongo_db import MongoDBPool

        pool = MongoDBPool()
        pool.close()

    def test_client_property_connects_if_needed(self):
        from shared.persistance.mongo_db import MongoDBPool

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_client_class.return_value = mock_client

            pool = MongoDBPool()
            _ = pool.client

            mock_client_class.assert_called_once()

    def test_get_mongo_client_dependency(self):
        from shared.persistance.mongo_db import MongoDBPool, get_mongo_client

        with patch("shared.persistance.mongo_db.MongoClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.admin.command.return_value = {"ok": 1}
            mock_client_class.return_value = mock_client

            from shared.persistance import mongo_db
            original_pool = mongo_db.mongo_pool

            mongo_db.mongo_pool = MongoDBPool()
            mongo_db.mongo_pool.connect("mongodb://localhost:27017")

            client = get_mongo_client()

            assert client is mock_client
            mongo_db.mongo_pool = original_pool
