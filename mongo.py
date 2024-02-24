from bson.objectid import ObjectId
import datetime

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
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()
    
    async def create_job(self):
        created_at = datetime.datetime.now(tz=datetime.timezone.utc)
        result = self.db['bio_api_jobs'].insert_one(
            {'created_at': created_at}
        )
        assert result.acknowledged == True
        return (str(result.inserted_id), created_at)

    async def mark_job_as_finished(self, job_id):
        finished_at = datetime.datetime.now(tz=datetime.timezone.utc)
        result = self.db['bio_api_jobs'].update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {'finished_at': finished_at}}
        )
        assert result.acknowledged == True
        return finished_at

    # Might throw pymongo.errors.DocumentTooLarge
    async def write_result_to_job(self, job_id, result):
        result = self.db['bio_api_jobs'].update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {'result': result}}
        )
        assert result.acknowledged == True

    async def get_field_data(
            self,
            collection:str,   # MongoDB collection
            mongo_ids:list,   # List of MongoDB ObjectIds as str
            field_paths:list, # List of field paths in dotted notation: ['some.example.field1', 'some.other.example.field2']
        ):
        filter = {'_id': {'$in': strs2ObjectIds(mongo_ids)}}
        document_count = self.db[collection].count_documents(filter)
        cursor = self.db[collection].find(filter, {field_path: True for field_path in field_paths})
        return document_count, cursor
