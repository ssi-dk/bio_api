from bson.objectid import ObjectId
import datetime
from os import getenv

from pydantic import BaseModel
import pymongo
from bson.objectid import ObjectId
from pathlib import Path

from pydantic_classes import DMXFromLocalFileRequest, DMXFromMongoDBRequest, DMXFromProfilesRequest, HCTreeCalcRequest

DMX_DIR = getenv('DMX_DIR', '/dmx_data')

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
    
    async def create_dmx_job(self, rq:DMXFromMongoDBRequest):
        created_at = datetime.datetime.now(tz=datetime.timezone.utc)
        result = self.db['dmx_jobs'].insert_one({
            'created_at': created_at,
            'status': 'new',
            'collection': rq.collection,
            'seqid_field_path': rq.seqid_field_path,
            'profile_field_path': rq.profile_field_path,
            'mongo_ids': rq.mongo_ids
            })
        assert result.acknowledged == True
        return (str(result.inserted_id), created_at)

    async def mark_job_as_finished(self, job_id):
        finished_at = datetime.datetime.now(tz=datetime.timezone.utc)
        result = self.db['bio_api_jobs'].update_one(
            {'_id': ObjectId(job_id)},
            {'$set': {'status': 'finished', 'finished_at': finished_at}}
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


class DistanceCalculation:
    conn: pymongo.MongoClient
    created_at: datetime.datetime or None
    finished_at: datetime.datetime or None
    status: str
    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    seq_mongo_ids: list
    id: str or None
    folder: Path or None

    def __init__(
            self,
            conn: pymongo.MongoClient,
            seq_collection: str,
            seqid_field_path: str,
            profile_field_path: str,
            seq_mongo_ids: list
            ):
        self.conn = conn
        self.seq_collection = seq_collection
        self.seqid_field_path = seqid_field_path
        self.profile_field_path = profile_field_path
        self.seq_mongo_ids = seq_mongo_ids
        self.status = 'new'
        self.created_at = datetime.datetime.now(tz=datetime.timezone.utc)
        result = self.conn.get_database()['dist_calculations'].insert_one({
            'created_at': self.created_at,
            'status': self.status,
            'seq_collection': self.seq_collection,
            'seqid_field_path': self.seqid_field_path,
            'profile_field_path': self.profile_field_path,
            'seq_mongo_ids': self.seq_mongo_ids
            })
        assert result.acknowledged == True
        self.id = str(result.inserted_id)

        self.folder = Path(DMX_DIR, self.id)
        self.folder.mkdir()