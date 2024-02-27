from bson.objectid import ObjectId
import datetime
from os import getenv
from pathlib import Path
from json import dump
import asyncio
from io import StringIO

from pydantic import BaseModel
import pymongo
from bson.objectid import ObjectId
from pandas import DataFrame, read_table
from pydantic_classes import DMXFromLocalFileRequest, DMXFromMongoDBRequest, DMXFromProfilesRequest, HCTreeCalcRequest

DMX_DIR = getenv('DMX_DIR', '/dmx_data')

def hoist(dict_element, field_path:str):
    """
    'Hoists' a deep dictionary element up to the surface :-)
    """
    for path_element in field_path.split('.'):
            dict_element = dict_element[path_element]
    return dict_element

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
        self.finished_at = None
        result = self.conn.get_database()['dist_calculations'].insert_one({
            'created_at': self.created_at,
            'finished_at': self.finished_at,
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
    
    async def mark_as_finished(self):
        result = self.conn.get_database()['dist_calculations'].update_one(
            {'id': self.id}, {'$update': {'finished_at': datetime.datetime.now(tz=datetime.timezone.utc)}}
        )
        assert result.acknowledged == True
    
    async def get_amx_as_dataframe(self, cursor):
        full_dict = dict()
        try:
            while True:
                mongo_item = next(cursor)
                sequence_id = hoist(mongo_item, self.seqid_field_path)
                allele_profile = hoist(mongo_item, self.profile_field_path)
                full_dict[sequence_id] = allele_profile
        except StopIteration:
            pass

        df = DataFrame.from_dict(full_dict, 'index', dtype=str)
        return df
    
    @property
    def allele_mx_filepath(self):
        return str(Path(DMX_DIR, self.id, 'allele_matrix.tsv'))
    
    async def save_amx_as_tsv(self, allele_mx_df):
        print("Allele mx as dataframe:")
        print(allele_mx_df)
        # Save allele matrix to a file that cgmlst-dists can use for input
        with open(self.allele_mx_filepath, 'w') as allele_mx_file_obj:
            allele_mx_file_obj.write("ID")  # Without an initial string in first line cgmlst-dists will fail!
            allele_mx_df.to_csv(allele_mx_file_obj, index = True, header=True, sep ="\t")
    
    async def dist_mx_from_allele_df(self):
        sp = await asyncio.create_subprocess_shell(f"cgmlst-dists {self.allele_mx_filepath}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
        stdout, stderr = await sp.communicate()

        await sp.wait()
        if sp.returncode != 0:
            errmsg = (f"Could not run cgmlst-dists on {self.allele_mx_filepath}!")
            raise OSError(errmsg + "\n\n" + stderr.decode('utf-8'))

        df = read_table(StringIO(stdout.decode('utf-8')))
        df.rename(columns = {"cgmlst-dists": "ids"}, inplace = True)
        df = df.set_index('ids')
        print("df from cgmlst-dists:")
        print(df)
        return df

    async def save_dmx_as_json(self, dist_mx_dict):
        print("Saving distance calculation as JSON")
        dist_mx_filepath = Path(self.folder, 'distance_matrix.json')
        with open(dist_mx_filepath, 'w') as dist_mx_file_obj:
            dump(dist_mx_dict, dist_mx_file_obj)
        
        
    @classmethod
    def find(cls, conn: pymongo.MongoClient, id: str):
        db = conn.get_database()
        doc = db['dist_calculations'].find_one({'_id': id})
        return cls(
            conn,
            seq_collection=doc['seq_collection'],
            seq_field_path=doc['seq_field_path'],
            profile_field_path=doc['profile_field_path'],
            seq_mongo_ids=doc['seq_mongo_ids'],
            status=doc['status'],
            created_at=doc['created_at'],
            finished_at=doc['finished_at']
            )