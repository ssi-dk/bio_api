import datetime
from os import getenv
from pathlib import Path
from json import dump, load
import asyncio
from io import StringIO
import abc

import pymongo
from bson.objectid import ObjectId
from pandas import DataFrame, read_table
from tree_maker import make_tree

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

class MissingDataException(Exception):
    pass

class MongoAPI:
    def __init__(self,
        connection_string: str,
    ):
        self.connection = pymongo.MongoClient(connection_string)
        self.db = self.connection.get_database()

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

connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
mongo_api = MongoAPI(connection_string)


class Calculation(metaclass=abc.ABCMeta):
    # Abstract base class
    id: str or None
    created_at: datetime.datetime or None
    finished_at: datetime.datetime or None
    status: str
    result: str or None = None

    def __init__(
            self,
            status: str = 'init',
            created_at: datetime.datetime or None = None,
            finished_at: datetime.datetime or None = None,
            id: str or None = None,
            result = None
            ):
        self.status = status
        self.created_at = created_at if created_at else datetime.datetime.now(tz=datetime.timezone.utc)
        self.finished_at = finished_at
        self.id = id
        self.result = result
    
    @abc.abstractproperty
    def collection(self):
        return 'my_collection'
    
    async def insert_document(self, **attrs):
        global_attrs = {
            'created_at': self.created_at,
            'finished_at': self.finished_at,
            'status': self.status,
            }
        doc_to_save = dict(global_attrs, **attrs)
        mongo_save = mongo_api.db[self.collection].insert_one(doc_to_save)
        assert mongo_save.acknowledged == True
        self.id = str(mongo_save.inserted_id)
        return self.id
    
    @classmethod
    def find(cls, id: str):
        """Return a class instance based on a particular MongoDB document.

        The class instance only contains the attributes that exist in the abstract Calculation class,
        and is primaryly intended for getting a status for the calculation.

        If id cannot be converted to an ObjectId, a bson.errors.InvalidId exception will be returned.
        If id can be converted but a document does not exist in this collection, None will be returned.
        """
        doc = mongo_api.db[cls.collection].find_one({'_id': ObjectId(id)})
        if doc is None:
            return None
        return cls(
            id=str(doc['_id']),
            created_at=doc['created_at'],
            finished_at=doc['finished_at'],
            status=doc['status'],
            result=doc.get('result', None)
            )
    
    async def get_field(self, field):
         doc = mongo_api.db[self.collection].find_one({'_id': ObjectId(self.id)}, {field: True})
         return doc[field]
    
    async def get_result(self):
        return await self.get_field('result')

    async def store_result(self, result):
        """Update the MongoDB document that corresponds with the class instance with a result.
        Also insert a timestamp for when the calculation was completed and mark the calculation as completed.
        """
        print(f"My collection: {self.collection}")
        update_result = mongo_api.db[self.collection].update_one(
            {'_id': ObjectId(self.id)}, {'$set': {
                'result': result,
                'finished_at': datetime.datetime.now(tz=datetime.timezone.utc),
                'status': 'completed'
                }}
        )
        assert update_result.acknowledged == True

    @abc.abstractmethod
    async def calculate(self, cursor):
        pass


class NearestNeighbors(Calculation):
    collection = 'nearest_neighbors'

    seq_collection: str
    profile_field_path: str
    input_mongo_id: str
    cutoff: int
    input_sequence: dict or None
    unknowns_are_diffs: bool = True

    def __init__(
            self,
            seq_collection: str or None=None,
            profile_field_path: str or None = None,
            input_mongo_id: str or None = None,
            cutoff: int or None=None,
            unknowns_are_diffs: bool = True,
            **kwargs):
        super().__init__(**kwargs)
        self.seq_collection = seq_collection
        self.profile_field_path = profile_field_path
        self.input_mongo_id = input_mongo_id
        self.unknowns_are_diffs = unknowns_are_diffs
        self.cutoff = cutoff
    
    async def insert_document(self):
        await super().insert_document(
            seq_collection=self.seq_collection,
            profile_field_path=self.profile_field_path,
            input_mongo_id=self.input_mongo_id,
            cutoff=self.cutoff,
            unknowns_are_diffs = self.unknowns_are_diffs,
        )
        return self.id

    async def query_mongodb_for_input_profile(self):
        "Get a the allele profile for the input sequence from MongoDB"
        profile_count, cursor = await mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.profile_field_path],
            mongo_ids=[self.input_mongo_id]
            )
        if profile_count == 0:
            message = f"Could not find the requested input sequence with mongo id {self.input_mongo_id}."
            raise MissingDataException(message)
        reference_profile = next(cursor)
        # TODO assert that reference sequence has the requested profile field
        return reference_profile
    
    def profile_diffs(self, other_profile:dict):
        """Count the number of differences between two allele profiles."""
        diff_count = 0
        for locus in self.input_sequence[self.profile_field_path].keys():
            try:
                ref_allele = int(self.input_sequence[self.profile_field_path][locus])
            except ValueError:
                if self.unknowns_are_diffs:
                    # Ref allele not intable - counting a difference.
                    diff_count += 1
                # No reason to compare alleles if ref allele is not intable
                continue
            try:
                other_allele = int(other_profile[locus])
                if ref_allele != other_allele:
                    # Both are intable but they are not equal - counting a difference.
                    diff_count += 1
            except ValueError:
                if self.unknowns_are_diffs:
                    # Other allele not intable - counting as difference.
                    diff_count += 1
        return diff_count
    
    async def calculate(self):
        print(f"Sequence collection: {self.seq_collection}")
        print(f"Profile field path: {self.profile_field_path}")
        comparable_sequences_count = mongo_api.db[self.seq_collection].count_documents({self.profile_field_path: {"$exists":True}})
        print(f"Comparable sequences found: {str(comparable_sequences_count)}")
        
        pipeline = list()
        pipeline.append(
            {'$match':
                {
                    self.profile_field_path: {'$exists': True},
                }
            }
        )
        pipeline.append(
            {'$project':
                {
                    # '_id': '_id', Probaly get this automatically
                    self.profile_field_path: 1,  # TODO un-nest dotted fields
                }
            }
        )
        sequences_to_compare_with = mongo_api.db[self.seq_collection].aggregate(pipeline)

        nearest_neighbors = list()
        for other_sequence in sequences_to_compare_with:
            if not other_sequence['_id'] == self.input_sequence['_id']:
                diff_count = self.profile_diffs(other_sequence[self.profile_field_path])
                if diff_count <= self.cutoff:
                    nearest_neighbors.append({'_id': other_sequence['_id'], 'diff_count': diff_count})
        self.result = sorted(nearest_neighbors, key=lambda x : x['diff_count'])
        await self.store_result(self.result)


class DistanceCalculation(Calculation):
    collection = 'dist_calculations'

    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    seq_mongo_ids: list

    def __init__(
            self,
            seq_collection: str or None=None,
            seqid_field_path: str or None = None,
            profile_field_path: str or None = None,
            seq_mongo_ids: list or None = None,
            **kwargs):
        super().__init__(**kwargs)
        self.seq_collection = seq_collection
        self.seqid_field_path = seqid_field_path
        self.profile_field_path = profile_field_path
        self.seq_mongo_ids = seq_mongo_ids
    
    async def insert_document(self):
        await super().insert_document(
            seq_collection=self.seq_collection,
            seqid_field_path=self.seqid_field_path,
            profile_field_path=self.profile_field_path,
            seq_mongo_ids=self.seq_mongo_ids,
        )
        Path(self.folder).mkdir()
        return self.id
    
    @property
    def folder(self):
        "Return the folder corresponding to the class instance"
        return Path(DMX_DIR, self.id)

    @property
    def allele_mx_filepath(self):
        "Return the filepath for the allele matrix file corresponding with the class instance"
        return str(Path(self.folder, 'allele_matrix.tsv'))
    
    @property
    def dist_mx_filepath(self):
        "Return the filepath for the distance matrix file corresponding with the class instance"
        return str(Path(self.folder, 'distance_matrix.json'))

    async def query_mongodb_for_allele_profiles(self):
        "Get a MongoDB cursor that represents the allele profiles for the calculation"
        profile_count, cursor = await mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.seqid_field_path, self.profile_field_path],
            mongo_ids=self.seq_mongo_ids
            )
        if len(self.seq_mongo_ids) != profile_count:
            message = "Could not find the requested number of sequences. " + \
                f"Requested: {str(len(self.seq_mongo_ids))}, found: {str(profile_count)}"
            raise MissingDataException(message)
        return profile_count, cursor

    async def _amx_df_from_mongodb_cursor(self, cursor):
        "Generate an allele matrix as dataframe containing the allele profiles from the MongoDB cursor"
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

    async def _save_amx_df_as_tsv(self, allele_mx_df):
        "Save allele matrix dataframe as TSV file"
        with open(self.allele_mx_filepath, 'w') as allele_mx_file_obj:
            allele_mx_file_obj.write("ID")  # Without an initial string in first line cgmlst-dists will fail!
            allele_mx_df.to_csv(allele_mx_file_obj, index = True, header=True, sep ="\t")

    async def _dmx_df_from_amx_tsv(self):
        "Generate a distance matrix dataframe from allele matrix TSV file"
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
        return df

    async def _save_dmx_as_json(self, dist_mx_dict):
        "Save distance matrix dataframe as JSON file"
        with open(self.dist_mx_filepath, 'w') as dist_mx_file_obj:
            dump(dist_mx_dict, dist_mx_file_obj)

    async def calculate(self, cursor):
        allele_mx_df: DataFrame = await self._amx_df_from_mongodb_cursor(cursor)
        await self._save_amx_df_as_tsv(allele_mx_df)
        dist_mx_df: DataFrame = await self._dmx_df_from_amx_tsv()
        dist_mx_dict = dist_mx_df.to_dict(orient='index')
        await self._save_dmx_as_json(dist_mx_dict)
        await self.store_result("Distance matrix stored on filesystem")
        print("Distance matrix calculation is finished!")


class TreeCalculation(Calculation):
    dmx_job: str
    method: str
    collection = 'tree_calculations'

    def __init__(self, dmx_job:str or None = None, method:str or None = None, **kwargs):
        super().__init__(**kwargs)
        self.dmx_job = dmx_job
        self.method = method
    
    async def calculate(self):
        dc = DistanceCalculation.find(self.dmx_job)
        with open(Path(dc.folder, 'distance_matrix.json')) as f:
            distances = load(f)
        try:
            dist_df: DataFrame = DataFrame.from_dict(distances, orient='index')
            tree = make_tree(dist_df, self.method)
            await self.store_result(tree)
        except ValueError:
            raise

