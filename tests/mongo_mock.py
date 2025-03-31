# tests/mongo_mock.py

from bson import ObjectId
from typing import Optional
import pymongo

def strs2ObjectIds(id_strings: list[str]):
    return [ObjectId(s) for s in id_strings]

class MongoAPI:
    """
    Provides access to general MongoDB collections with optional ObjectId filtering and field projections.
    Used for reading and querying data across collections.

    Return cursor to iterate through mongo query results
    """
    def __init__(self, connection_string: str = None, db=None):
        if db is not None:
            self.db = db  # Injected in-memory Mongo instance for testing
        else:
            self.connection = pymongo.MongoClient(connection_string, directConnection=True)
            self.db = self.connection.get_database()

    async def get_field_data(self, collection: str, mongo_ids: Optional[list], field_paths: list):
        """
        Return (document count, cursor) from a collection, with optional filtering by ObjectIds and field projection.
        """
        if mongo_ids:
            filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}
            projection = {field_path: True for field_path in field_paths}
            count = self.db[collection].count_documents(filter)
            cursor = self.db[collection].find(filter, projection)
        else:
            projection = {field_path: True for field_path in field_paths}
            count = self.db[collection].count_documents({})
            cursor = self.db[collection].find({}, projection)
        return count, cursor

class MongoConfig:
    """
    Makes it possible to extract information from the mock mongo, insert, update
    """
    def __init__(self, mongoapi: MongoAPI):
        self.mongoapi = mongoapi
        self.collection_name = "BioAPI_config"

    def get_section(self, section):
        """Retrieve a config section by name"""
        return self.mongoapi.db[self.collection_name].find_one({'section': section})

    def set_section(self, section: str, config: dict):
        """Insert or update a config section with upsert"""
        return self.mongoapi.db[self.collection_name].replace_one(
            {'section': section}, config, upsert=True
        )

    def load(self, config: list[dict]):
        """Bulk-insert a list of config documents"""
        self.mongoapi.db[self.collection_name].insert_many(config)
