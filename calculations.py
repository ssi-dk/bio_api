import datetime
from os import getenv
from pathlib import Path
import asyncio
from io import StringIO
import abc
from dataclasses import dataclass, field, asdict
from abc import abstractmethod

from bson.objectid import ObjectId
from pandas import DataFrame, read_table, read_csv

from mongo import MongoAPI
from tree_maker import make_tree

import sofi_messenger
from mongo import Config

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')

DMX_DIR = getenv('DMX_DIR', '/dmx_data')
AMQP_HOST = getenv('AMQP_HOST', "amqp://guest:guest@rabbitmq/")

messenger = sofi_messenger.SOFIMessenger(AMQP_HOST)

class MissingDataException(Exception):
    pass

def hoist(var, dotted_field_path:str):
    """
    'Hoists' a value from a nested dictionary element up to the surface.

    Example:
    var = {'my': {'nested': {'dictionary': 123}}}
    dotted_field_path = 'my.nested.dictionary'
    print(hoist(var, dotted_field_path))

    The above example should return 123.
    """
    for path_element in dotted_field_path.split('.'):
            var = var[path_element]
    return var


@dataclass
class HPCResources:
    cpus: int | None = None
    memGB: int | None = None
    group: str | None = None
    nodes: str | None = None
    walltime: str | None = None


class Calculation(metaclass=abc.ABCMeta):
    # Abstract base class
    mongo_api: MongoAPI
    created_at: datetime.datetime | None
    finished_at: datetime.datetime | None
    status: str
    result: str | None = None

    def __init__(
            self,
            status: str = 'init',
            created_at: datetime.datetime | None = None,
            finished_at: datetime.datetime | None = None,
            _id: ObjectId | None = None,
            result = None
            ):
        self.status = status
        self.created_at = created_at if created_at else datetime.datetime.now(tz=datetime.timezone.utc)
        self.finished_at = finished_at
        self._id = _id
        self.result = result
        self.config = Config(Calculation.mongo_api)

    @classmethod
    def set_mongo_api(cls,mongo_api):
        cls.mongo_api = mongo_api

    def to_dict(self):
        content = dict()
        for key, value in vars(self).items():
            if isinstance(value, datetime.datetime):
                content[key] = value.isoformat()
            elif isinstance(value, HPCResources):
                content[key] = asdict[value]
            elif key == '_id':
                content['job_id'] = str(value)
            else:
                content[key] = value
        return content
    
    # https://stackoverflow.com/questions/2736255/abstract-attributes-in-python
    
    @property
    @abc.abstractmethod
    def collection(self) -> str:
        ...

    async def insert_document(self, **attrs):
        global_attrs = {
            'status': self.status,
            'created_at': self.created_at,
            'finished_at': self.finished_at,
            'result': self.result
            }
        doc_to_save = dict(global_attrs, **attrs)
        print(f"Doc to save: {doc_to_save}")
        coll = Calculation.mongo_api.db[self.collection]

        mongo_save = Calculation.mongo_api.db[self.collection].insert_one(doc_to_save)
        assert mongo_save.acknowledged == True
        self._id = mongo_save.inserted_id
        print(f"_id: {self._id}")
        return self._id

    @classmethod
    def recall(cls, id: str):
        """Return a class instance based on a particular MongoDB document.
        """
        doc = cls.mongo_api.db[cls.collection].find_one({'_id': ObjectId(id)})
        if doc is None:
            return None
        return cls(**doc)

        
    async def get_field(self, field):
        doc = Calculation.mongo_api.db[self.collection].find_one({'_id': self._id}, {field: True})
        return doc[field]
    
    async def get_result(self):
        return await self.get_field('result')

    async def store_result(self, result, status:str='completed'):
        """Update the MongoDB document that corresponds with the class instance with a result.
        Also insert a timestamp for when the calculation was completed and mark the calculation as completed.
        """
        print("Store result.")
        print(f"My collection: {self.collection}")
        print("My _id:")
        print(self._id)
        update_result = Calculation.mongo_api.db[self.collection].update_one(
            {'_id': self._id}, {'$set': {
                'result': result,
                'finished_at': datetime.datetime.now(tz=datetime.timezone.utc),
                'status': status
                }
            }
        )
        assert update_result.acknowledged == True

    async def update(self):
        """Update the MongoDB document that corresponds with the class instance.
        """
        print("Update.")
        print(f"My collection: {self.collection}")
        print("My _id:")
        print(self._id)
        print("__dict__:")
        print(self.__dict__)
        update_result = Calculation.mongo_api.db[self.collection].update_one(
            {'_id': self._id}, {'$set': {
                    **vars(self)
                }
            }
        )
        assert update_result.acknowledged == True

    @abc.abstractmethod
    async def calculate(self, cursor):
        pass


class NearestNeighbors(Calculation):
    collection = 'nearest_neighbors'

    seq_collection: str
    filtering: dict = dict()
    profile_field_path: str
    input_mongo_id: str
    cutoff: int
    unknowns_are_diffs: bool = True
    input_sequence: dict | None

    @property
    def input_profile(self):
        return hoist(self.input_sequence, self.profile_field_path)

    def __init__(
            self,
            input_mongo_id: str | None = None,
            cutoff: int | None=None,
            unknowns_are_diffs: bool = True,
            **kwargs):
        super().__init__(**kwargs)
        NN_config = self.config.get_section(self.collection)     
        self.seq_collection = NN_config.get("seq_collection")
        self.filtering = NN_config.get("filtering")
        self.profile_field_path = NN_config.get("profile_field_path")
        self.input_mongo_id = input_mongo_id
        self.unknowns_are_diffs = unknowns_are_diffs
        self.cutoff = cutoff #NN_config.get("cutoff",cutoff)

    async def insert_document(self):
        await super().insert_document(
            seq_collection=self.seq_collection,
            profile_field_path=self.profile_field_path,
            filtering=self.filtering,
            input_mongo_id=self.input_mongo_id,
            cutoff=self.cutoff,
            unknowns_are_diffs = self.unknowns_are_diffs,
            # self.input_sequence is intentionally not stored as it is already stored in the sequence document
        )
        return self._id

    async def query_mongodb_for_input_profile(self):
        "Get a the allele profile for the input sequence from MongoDB"
        profile_count, cursor = await Calculation.mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.profile_field_path],
            mongo_ids=[self.input_mongo_id]
            )
        if profile_count == 0:
            message = f"Could not find a document with id {self.input_mongo_id} in collection {self.seq_collection}."
            raise MissingDataException(message)
        reference_profile = next(cursor)
        return reference_profile
    
    def profile_diffs(self, other_profile:dict):
        """Count the number of differences between two allele profiles."""
        diff_count = 0
        for locus in self.input_profile.keys():
            try:
                ref_allele = int(self.input_profile[locus])
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
        comparable_sequences_count = Calculation.mongo_api.db[self.seq_collection].count_documents({self.profile_field_path: {"$exists":True}})
        print(f"Comparable sequences found: {str(comparable_sequences_count)}")
        
        pipeline = list()

        print("Filters to apply to sequences before running nearest neighbors:")
        # There must always be a filter on species as different species have different cgMLST schemas
        try:
            for k, v in self.filtering.items():
                print(f"{k} must be {v}")
                pipeline.append(
                {'$match':
                    {
                        k: {'$eq': v},
                    }
                }
            )
        except KeyError as e:
            await self.store_result(str(e), 'error')

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
                    self.profile_field_path: 1,
                }
            }
        )
        sequences_to_compare_with = Calculation.mongo_api.db[self.seq_collection].aggregate(pipeline)

        nearest_neighbors = list()
        for other_sequence in sequences_to_compare_with:
            if not other_sequence['_id'] == self.input_sequence['_id']:
                diff_count = self.profile_diffs(hoist(other_sequence, self.profile_field_path))
                if diff_count <= self.cutoff:
                    nearest_neighbors.append({'_id': other_sequence['_id'], 'diff_count': diff_count})
        self.result = sorted(nearest_neighbors, key=lambda x : x['diff_count'])
        await self.store_result(self.result)
    
    def to_dict(self):
        content = super().to_dict()
        if 'result' in content:
            # Add id, remove _id from result
            r: dict
            for r in content['result']:
                r['id'] = str(r['_id'])
                r.pop('_id')

        return content

class DistanceCalculation(Calculation):
    collection = 'dist_calculations'

    seq_collection: str
    seqid_field_path: str
    profile_field_path: str
    seq_mongo_ids: list | None

    def __init__(
            self,
            seq_mongo_ids: list | None = None,
            **kwargs):
        super().__init__(**kwargs)

        Dist_config = self.config.get_section(self.collection)     
        self.seq_collection = Dist_config.get("seq_collection")
        self.seqid_field_path = Dist_config.get("seqid_field_path")
        self.profile_field_path = Dist_config.get("profile_field_path")
        self.seq_mongo_ids = seq_mongo_ids
    
    async def insert_document(self):
        await super().insert_document(
            seq_collection=self.seq_collection,
            seqid_field_path=self.seqid_field_path,
            profile_field_path=self.profile_field_path,
            seq_mongo_ids=self.seq_mongo_ids,
        )
        Path(self.folder).mkdir()
        return self._id
    
    @property
    def folder(self):
        "Return the folder corresponding to the class instance"
        return Path(DMX_DIR, self.to_dict()['job_id'])

    @property
    def allele_mx_filepath(self):
        "Return the filepath for the allele matrix file corresponding with the class instance"
        return str(Path(self.folder, 'allele_matrix.tsv'))
    
    @classmethod
    def get_dist_mx_filename(cls):
        return 'distance_matrix.csv'

    @property
    def dist_mx_filepath(self):
        "Return the filepath for the distance matrix file corresponding with the class instance"
        return str(Path(self.folder, self.get_dist_mx_filename()))

    async def query_mongodb_for_allele_profiles(self):
        "Get a MongoDB cursor that represents the allele profiles for the calculation"
        profile_count, cursor = await Calculation.mongo_api.get_field_data(
            collection=self.seq_collection,
            field_paths=[self.seqid_field_path, self.profile_field_path],
            mongo_ids=self.seq_mongo_ids
            )
        if self.seq_mongo_ids is not None and len(self.seq_mongo_ids) != profile_count:
            message = "Could not find the requested number of sequences. " + \
                f"Requested: {str(len(self.seq_mongo_ids))}, found: {str(profile_count)}"
            raise MissingDataException(message)
        return profile_count, cursor

    async def _amx_df_from_mongodb_cursor(self, cursor):
        ("Generate an allele matrix as dataframe containing the allele profiles from the MongoDB cursor. ")
        ("At the same time, generate a dict for tracing sequence IDs back to mongo IDs.")
        ("The dict will be stored in the calculation document.")
        full_dict = dict()
        mongo_ids = dict()

        try:
            while True:
                mongo_item = next(cursor)
                try:
                    sequence_id = hoist(mongo_item, self.seqid_field_path)
                except KeyError:
                    raise MissingDataException(f"Sequence document with id {str(mongo_item['_id'])} does not contain sequence id field path '{self.seqid_field_path}'.")
                try:
                    allele_profile = hoist(mongo_item, self.profile_field_path)
                    full_dict[sequence_id] = allele_profile
                    mongo_ids[sequence_id] = mongo_item['_id']
                except KeyError:
                    raise MissingDataException(f"Sequence document with id {str(mongo_item['_id'])} does not contain profile field path '{self.profile_field_path}'.")
        except StopIteration:
            pass

        df = DataFrame.from_dict(full_dict, 'index', dtype=str)
        return df, mongo_ids

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

    async def calculate(self, cursor):
        try:
            allele_mx_df, mongo_ids_dict = await self._amx_df_from_mongodb_cursor(cursor)
            await self._save_amx_df_as_tsv(allele_mx_df)  # The allele mx is only saved as documentation
            dist_mx_df: DataFrame = await self._dmx_df_from_amx_tsv()
            dist_mx_df.to_csv(path_or_buf=self.dist_mx_filepath)

            # We do not store the distance matrix in MongoDB because it might grow to more than 16 MB.
            # Instead we just store a dictionary of sequence IDs and their related mongo IDs.
            await self.store_result({'seq_to_mongo': mongo_ids_dict})
            print("Distance matrix calculation is finished!")
        except MissingDataException as e:
            await self.store_result(str(e), 'error')


class TreeCalculation(Calculation):
    dmx_job: str
    method: str
    collection = 'tree_calculations'

    def __init__(self, dmx_job:str | None = None, method:str | None = None, **kwargs):
        super().__init__(**kwargs)
        self.dmx_job = dmx_job
        self.method = method
    
    async def insert_document(self):
        await super().insert_document(
            dmx_job=self.dmx_job,
            method=self.method
        )
        return self._id

    async def calculate(self):
        dc = DistanceCalculation.recall(self.dmx_job)
        try:
            dist_df: DataFrame = read_csv(Path(dc.folder, DistanceCalculation.get_dist_mx_filename()), index_col=0)
            tree = make_tree(dist_df, self.method)
            print("Newick:")
            print(tree)
            await self.store_result(tree)
        except ValueError as e:
            await self.store_result(str(e), 'error')


class HPCCalculation(Calculation):
    @property
    @abstractmethod
    def job_type(self):
        pass

    hpc_resources: HPCResources | None = None

    def __init__(
        self,
        hpc_resources: HPCResources | None = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.hpc_resources = hpc_resources
    
    async def calculate(self, args:dict|None=None):
        print("Running calculate on HPCCalculation")
        print(f"uuid: {str(self._id)}")
        print(f"job_type: {self.job_type}")
        print("args:")
        print(args)
        hpc_resources = asdict(self.hpc_resources)
        print("hpc_resources:")
        print(hpc_resources)
        await messenger.send_hpc_call(
            uuid=str(self._id),
            job_type=self.job_type,
            args=args,
            **hpc_resources
        )

class DebugCalculation(HPCCalculation):
    collection = 'debug'

    @property
    def job_type(self):
        return 'debug'
    
    async def calculate(self, args:str|None=None):
        print("Running calculate on DebugCalculation")
        await super().calculate(args={'sleep': '2'})

class SNPCalculation(HPCCalculation):
    collection = 'snp'
    seq_collection: str
    seqid_field_path: str
    seq_mongo_ids: list
    reference_mongo_id: str
    depth: int = 15
    ignore_hz: bool
    input_filenames: list = list()
    reference_filename: str | None = None

    def __init__(
            self,
            seq_mongo_ids: list,
            reference_mongo_id: str,
            depth: int = 15,
            ignore_hz: bool=True,
            **kwargs
            ):
        super().__init__(**kwargs)

        SNP_config = self.config.get_section(self.collection)     
        self.seq_collection = SNP_config.get("seq_collection")
        self.seqid_field_path = SNP_config.get("seqid_field_path")
        self.fastq_field_path = SNP_config.get("fastq_field_path")
        self.contigs_field_path = SNP_config.get("contigs_field_path")
        self.hpc_resources = SNP_config.get("hpc_resources",{})
        
        self.seq_mongo_ids = seq_mongo_ids
        self.reference_mongo_id = reference_mongo_id
        self.depth = depth
        self.ignore_hz = ignore_hz
        self.hpc_resources = hpc_resources

    @property
    def job_type(self):
        return 'snp'

    async def insert_document(self):
        await super().insert_document(
            seq_collection=self.seq_collection,
            seqid_field_path=self.seqid_field_path,
            seq_mongo_ids=self.seq_mongo_ids,
            reference_mongo_id=self.reference_mongo_id,
            depth=self.depth,
            ignore_hz=self.ignore_hz,
            input_filenames=self.input_filenames,
            reference_filename=self.reference_filename,
            hpc_resources = asdict(self.hpc_resources)
        )
        return self._id
    
    async def query_mongodb_for_filenames(self):
    
        # Get the filenames for the samples
        sequence_count, cursor = await Calculation.mongo_api.get_field_data(
            collection=self.seq_collection,
            mongo_ids=self.seq_mongo_ids,
            field_paths=[ self.fastq_field_path ],
            )

        # Check that we found the correct number of sample documents
        if self.seq_mongo_ids is not None and len(self.seq_mongo_ids) != sequence_count:
            message = "Could not find the requested number of samples. " + \
                f"Requested: {str(len(self.seq_mongo_ids))}, found: {str(sequence_count)}"
            raise MissingDataException(message)

        # Add filenames to object
        try:
            while True:
                self.input_filenames.append(hoist(next(cursor), self.fastq_field_path))
        except StopIteration:
            pass
    
        # Get the reference filename
        sequence_count, cursor = await self.mongo_api.get_field_data(
            collection=self.seq_collection,
            mongo_ids=[ self.reference_mongo_id ],
            field_paths=[ self.contigs_field_path ],
            )
        assert sequence_count == 1
        self.reference_filename = hoist(next(cursor), self.contigs_field_path)

        return self.input_filenames, self.reference_filename
    
    async def calculate(self):
        #TODO merge with calculate on HPCCalculation
        calc_input_params =             {
                'input_files': self.input_filenames,
                'reference': self.reference_filename,
                'depth': self.depth,
                'ignore_heterozygous': 'TRUE' if self.ignore_hz else 'FALSE'
            }
        print("Calculation input params:")
        print(calc_input_params)
        hpc_resources = asdict(self.hpc_resources)
        print("HPC resources:")
        print(hpc_resources)

        await messenger.send_hpc_call(
            uuid=str(self._id),
            job_type=self.job_type,
            args=calc_input_params,
            **hpc_resources
        )