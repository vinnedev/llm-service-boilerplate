import pytest
from datetime import datetime, timezone

from pymongo import MongoClient


pytestmark = [pytest.mark.integration, pytest.mark.slow]


class TestMongoDBConnection:
    def test_connection_established(self, mongodb_client: MongoClient):
        result = mongodb_client.admin.command("ping")

        assert result["ok"] == 1.0

    def test_database_operations(self, test_database):
        collection = test_database["test_collection"]

        doc = {"name": "test", "value": 123}
        result = collection.insert_one(doc)
        assert result.inserted_id is not None

        retrieved = collection.find_one({"name": "test"})
        assert retrieved is not None
        assert retrieved["value"] == 123

        collection.update_one({"name": "test"}, {"$set": {"value": 456}})
        updated = collection.find_one({"name": "test"})
        assert updated["value"] == 456

        collection.delete_one({"name": "test"})
        deleted = collection.find_one({"name": "test"})
        assert deleted is None

    def test_collection_isolation(self, test_database):
        col1 = test_database["collection_1"]
        col2 = test_database["collection_2"]

        col1.insert_one({"data": "col1"})
        col2.insert_one({"data": "col2"})

        assert col1.count_documents({}) == 1
        assert col2.count_documents({}) == 1
        assert col1.find_one()["data"] == "col1"
        assert col2.find_one()["data"] == "col2"

    def test_index_creation(self, test_database):
        collection = test_database["indexed_collection"]

        collection.create_index("email", unique=True)

        collection.insert_one({"email": "test@example.com"})

        with pytest.raises(Exception):
            collection.insert_one({"email": "test@example.com"})

    def test_query_with_filters(self, test_database):
        collection = test_database["query_test"]

        docs = [
            {"name": "Alice", "age": 25, "active": True},
            {"name": "Bob", "age": 30, "active": True},
            {"name": "Charlie", "age": 35, "active": False},
        ]
        collection.insert_many(docs)

        active_users = list(collection.find({"active": True}))
        assert len(active_users) == 2

        adults = list(collection.find({"age": {"$gte": 30}}))
        assert len(adults) == 2

        bob = collection.find_one({"name": "Bob"})
        assert bob["age"] == 30

    def test_sorting_and_limiting(self, test_database):
        collection = test_database["sort_test"]

        for i in range(10):
            collection.insert_one({"order": i, "created_at": datetime.now(timezone.utc)})

        ascending = list(collection.find().sort("order", 1).limit(3))
        assert [d["order"] for d in ascending] == [0, 1, 2]

        descending = list(collection.find().sort("order", -1).limit(3))
        assert [d["order"] for d in descending] == [9, 8, 7]

    def test_find_one_and_update(self, test_database):
        collection = test_database["update_test"]

        collection.insert_one({"counter": 0, "name": "test"})

        updated = collection.find_one_and_update(
            {"name": "test"},
            {"$inc": {"counter": 1}},
            return_document=True
        )

        assert updated["counter"] == 1

    def test_aggregation_pipeline(self, test_database):
        collection = test_database["agg_test"]

        docs = [
            {"category": "A", "value": 10},
            {"category": "A", "value": 20},
            {"category": "B", "value": 30},
        ]
        collection.insert_many(docs)

        pipeline = [
            {"$group": {"_id": "$category", "total": {"$sum": "$value"}}},
            {"$sort": {"_id": 1}}
        ]
        results = list(collection.aggregate(pipeline))

        assert len(results) == 2
        assert results[0]["_id"] == "A"
        assert results[0]["total"] == 30
        assert results[1]["_id"] == "B"
        assert results[1]["total"] == 30

    def test_datetime_handling(self, test_database):
        collection = test_database["datetime_test"]

        now = datetime.now(timezone.utc)
        collection.insert_one({"timestamp": now, "event": "test"})

        retrieved = collection.find_one({"event": "test"})

        assert retrieved["timestamp"] is not None

    def test_bulk_operations(self, test_database):
        collection = test_database["bulk_test"]

        docs = [{"index": i} for i in range(100)]
        result = collection.insert_many(docs)

        assert len(result.inserted_ids) == 100
        assert collection.count_documents({}) == 100

    def test_text_search(self, test_database):
        collection = test_database["text_search_test"]

        collection.create_index([("content", "text")])

        docs = [
            {"content": "Python is a great programming language"},
            {"content": "MongoDB is a NoSQL database"},
            {"content": "FastAPI uses Python for web development"},
        ]
        collection.insert_many(docs)

        results = list(collection.find({"$text": {"$search": "Python"}}))

        assert len(results) == 2
