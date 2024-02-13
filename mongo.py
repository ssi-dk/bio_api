from bson.objectid import ObjectId

from pathlib import Path

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
        connection_string: str
    ):
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()
    
    async def get_field_data(
            self,
            collection:str,
            mongo_ids:list,
            field_path:str,
        ):
        filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}
        document_count = self.db[collection].count_documents(filter)
        cursor = self.db[collection].find(filter, {field_path: True})
        return document_count, cursor