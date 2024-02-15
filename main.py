from os import getenv
import uuid
from typing import Union
from io import StringIO
from pathlib import Path
import traceback
import asyncio

from pydantic import BaseModel
from fastapi import FastAPI
from pandas import DataFrame, read_table

import mongo
from tree_maker import make_tree
# from qstat import consume_qstat

app = FastAPI()
connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
mongo_api = mongo.MongoAPI(connection_string)

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
GENERATED_MX_DIR = getenv('BIO_API_DATA_DIR', '/data')


class ProcessingRequest(BaseModel):
    id: Union[None, uuid.UUID]
    timeout: int = 2

    def __init__(self, **kwargs):
        super().__init__( **kwargs)
        self.id = uuid.uuid4()

class DMXFromMongoDBRequest(BaseModel):
    collection: str
    seqid_field_path: str
    profile_field_path: str
    mongo_ids: list

class DMXFromProfilesRequest(BaseModel):
    loci: set
    profiles: dict

class DMXFromLocalFileRequest(BaseModel):
    file_path: str

class HCTreeCalcRequest(ProcessingRequest):
    """Represents a REST request for a tree calculation based on hierarchical clustering.
    """
    distances: dict
    method: str


async def allele_mx_from_bifrost_mongo(mongo_cursor):
    # Generate an allele matrix with all the allele profiles from the mongo cursor.
    full_dict = dict()
    try:
        first_mongo_item = next(mongo_cursor)
    except StopIteration:
        raise
    first_row = mongo.get_alleles(first_mongo_item)
    full_dict[mongo.get_sequence_id(first_mongo_item)] = first_row
    allele_names = set(first_row.keys())
    for mongo_item in mongo_cursor:
        row = mongo.get_alleles(mongo_item)
        row_allele_names = set(row.keys())
        assert row_allele_names == allele_names
        full_dict[mongo.get_sequence_id(mongo_item)] = row
    return DataFrame.from_dict(full_dict, 'index', dtype=str)

def hoist(dict_element, field_path:str):
    """
    'Hoists' a deep dictionary element up to the surface :-)
    """
    for path_element in field_path.split('.'):
            dict_element = dict_element[path_element]
    return dict_element

async def allele_mx_from_mongodb(cursor, seqid_field_path: str, profile_field_path: str):
    # Generate an allele matrix with all the allele profiles from the mongo cursor.

    full_dict = dict()

    try:
        while True:
            mongo_item = next(cursor)
            sequence_id = hoist(mongo_item, seqid_field_path)
            allele_profile = hoist(mongo_item, profile_field_path)
            full_dict[sequence_id] = allele_profile
    except StopIteration:
        pass

    df = DataFrame.from_dict(full_dict, 'index', dtype=str)
    return df

async def dist_mx_from_allele_df(allele_mx:DataFrame, job_id: uuid.UUID):
    print("Allele mx:")
    print(allele_mx)
    # save allele matrix to a file that cgmlst-dists can use for input
    allele_mx_filepath = Path(GENERATED_MX_DIR, f'allele_matrix_{job_id.hex}.tsv')
    with open(allele_mx_filepath, 'w') as allele_mx_file_obj:
        allele_mx_file_obj.write("ID")  # Without an initial string in first line cgmlst-dists will fail!
        allele_mx.to_csv(allele_mx_file_obj, index = True, header=True, sep ="\t")
    sp = await asyncio.create_subprocess_shell(f"cgmlst-dists {str(allele_mx_filepath)}",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await sp.communicate()

    await sp.wait()
    if sp.returncode != 0:
        errmsg = (f"Could not run cgmlst-dists on {str(allele_mx_filepath)}!")
        raise OSError(errmsg + "\n\n" + stderr.decode('utf-8'))

    df = read_table(StringIO(stdout.decode('utf-8')))
    df.rename(columns = {"cgmlst-dists": "ids"}, inplace = True)
    df = df.set_index('ids')
    print("df from cgmlst-dists:")
    print(df)
    return df

async def calculate_dmx_from_file(file_path: str):
    sp = await asyncio.create_subprocess_shell(f"cgmlst-dists {file_path}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await sp.communicate()

    await sp.wait()
    if sp.returncode != 0:
        errmsg = (f"Could not run cgmlst-dists on {str(file_path)}!")
        raise OSError(errmsg + "\n\n" + stderr.decode('utf-8'))

    df = read_table(StringIO(stdout.decode('utf-8')))
    df.rename(columns = {"cgmlst-dists": "ids"}, inplace = True)
    df = df.set_index('ids')
    print("df from cgmlst-dists:")
    print(df)
    return df

@app.get("/")
def root():
    return {"message": "Hello World"}

def validate_profiles(loci: set, profiles:dict):
    for profile in profiles.values():
        dict_keys_set = set(profile.keys())
        assert dict_keys_set == loci

@app.post("/v1/distance_matrix/from_request")
async def dmx_from_request(rq: DMXFromProfilesRequest):
    """
    Return a distance matrix from allele profiles that are included directly in the request
    """
    # TODO: turn this into a decorator that can be applied to all API requests
    job_id = uuid.uuid4()
    
    print("Requested distance matrix from allele profile")
    print(f"Locus count: {len(rq.loci)}")
    print(f"Profile count: {len(rq.profiles)}")

    validate_profiles(rq.loci, rq.profiles)
    print("Profiles validated")

    allele_mx_df = DataFrame.from_dict(rq.profiles, 'index', dtype=str)
    dist_mx_df: DataFrame = await dist_mx_from_allele_df(allele_mx_df, job_id)
    return {
        "job_id": job_id,
        "distance_matrix": dist_mx_df.to_dict(orient='tight')
        }

@app.post("/v1/distance_matrix/from_local_file")
async def dmx_from_local_file(rq: DMXFromLocalFileRequest):
    """
    Return a distance matrix from allele profiles defined in a local tsv file in the Bio API container
    """
    job_id = uuid.uuid4()
    dist_mx_df: DataFrame = await calculate_dmx_from_file(rq.file_path)
    return {
        'job_id': job_id,
        'distance_matrix': dist_mx_df.to_dict(orient='tight')
        }

@app.post("/v1/distance_matrix/from_mongodb")
async def dmx_from_mongodb(rq: DMXFromMongoDBRequest):
    """
    Return a distance matrix from allele profiles defined in MongoDB documents
    """
    job_id = uuid.uuid4()
    profile_count, cursor = await mongo_api.get_field_data(
        collection=rq.collection,
        field_paths=[rq.seqid_field_path, rq.profile_field_path],
        mongo_ids=rq.mongo_ids
        )
    
    if len(rq.mongo_ids) != profile_count:
        return {
            'status': 'ERROR',
            'error_msg:': "Could not find the requested number of sequences. " + \
                f"Requested: {str(len(rq.mongo_ids))}, found: {str(profile_count)}"
        }

    allele_mx_df: DataFrame = await allele_mx_from_mongodb(cursor, rq.seqid_field_path, rq.profile_field_path)
    # ERROR: row 3 had 559 cols, expected 4000
    # dist_mx_df: DataFrame = await dist_mx_from_allele_df(allele_mx_df, job_id)
    return {
        'job_id': job_id,
        'status': 'OK',
        'profile_count': profile_count,
        #"distance_matrix": dist_mx_df.to_dict(orient='tight')
        }

#^^^ NEW

@app.post("/tree/hc/")
async def hc_tree(rq: HCTreeCalcRequest):
    response = {"job_id": rq.id, "method": rq.method}
    try:
        dist_df: DataFrame = DataFrame.from_dict(rq.distances, orient='index')
        tree = make_tree(dist_df, rq.method)
        response['tree'] = tree
    except ValueError as e:
        response['error'] = str(e)
        print(traceback.format_exc())
    return response
