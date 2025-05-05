import pymongo
from bson.objectid import ObjectId

def strs2ObjectIds(id_strings: list):
    """
    Converts a list of strings to a set of ObjectIds
    """
    output = list()
    for id_str in id_strings:
        output.append(ObjectId(id_str))
    return output


class MongoAPI:
    def __init__(self,
        connection_string: str,
    ):
        self.connection = pymongo.MongoClient(connection_string, directConnection=True)
        self.db = self.connection.get_database()

    async def get_field_data(
            self,
            collection:str,   # MongoDB collection
            mongo_ids:list | None,   # List of MongoDB ObjectIds as str
            field_paths:list, # List of field paths in dotted notation: ['some.example.field1', 'some.other.example.field2']
        ):
        if mongo_ids:
            filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}
            document_count = self.db[collection].count_documents(filter)
            cursor = self.db[collection].find(filter, {field_path: True for field_path in field_paths})
        else:
            document_count = self.db[collection].count_documents({})
            cursor = self.db[collection].find({}, {field_path: True for field_path in field_paths})
        return document_count, cursor

class Config:
    def __init__(self, mongoapi: MongoAPI):
        self.mongoapi = mongoapi
        self.collection_name = "BioAPI_config"
    def get_section(self, section):
        return self.mongoapi.db[self.collection_name].find_one({'section':section})
    def set_section(self, section: str, config: dict):
        return self.mongoapi.db[self.collection_name].replace_one(
            {'section': section},
            config,
            upsert = True) 
    def load(self, config: dict):
        self.mongoapi.db[self.collection_name].insert_many(config)
    def clear(self):
        self.mongoapi.db[self.collection_name].remove({})
