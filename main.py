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
mongo_api = mongo.MongoAPI(getenv('MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test'))

TMPDIR = getenv('TMPDIR', '/tmp')
DATADIR = getenv('DATADIR', '/data')


class ProcessingRequest(BaseModel):
    id: Union[None, uuid.UUID]
    timeout: int = 2

    def __init__(self, **kwargs):
        super().__init__( **kwargs)
        self.id = uuid.uuid4()

class DMXFromMongoIsdRequest(ProcessingRequest):
    collection: str
    path_elements: list
    mongo_ids: set

class DMXFromProfilesRequest(BaseModel):
    loci: set
    profiles: dict

class DMXFromLocalFileRequest(BaseModel):
    file_name: str

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

async def dist_mx_from_allele_df(allele_mx:DataFrame, job_id: uuid.UUID):
    print("Allele mx:")
    print(allele_mx)
    # save allele matrix to a file that cgmlst-dists can use for input
    allele_mx_path = Path(TMPDIR, f'allele_matrix_{job_id.hex}.tsv')
    with open(allele_mx_path, 'w') as allele_mx_file_obj:
        allele_mx_file_obj.write("ID")  # Without an initial string in first line cgmlst-dists will fail!
        allele_mx.to_csv(allele_mx_file_obj, index = True, header=True, sep ="\t")
    sp = await asyncio.create_subprocess_shell(f"cgmlst-dists {str(allele_mx_path)}",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await sp.communicate()

    await sp.wait()
    if sp.returncode != 0:
        errmsg = (f"Could not run cgmlst-dists on {str(allele_mx_path)}!")
        raise OSError(errmsg + "\n\n" + stderr.decode('utf-8'))

    df = read_table(StringIO(stdout.decode('utf-8')))
    df.rename(columns = {"cgmlst-dists": "ids"}, inplace = True)
    df = df.set_index('ids')
    print("df from cgmlst-dists:")
    print(df)
    return df

async def dist_mx_from_local_file(file_name: str):
    print(f"File name: {file_name}")
    file_path = Path(DATADIR, file_name)
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
    print("Requested distance matrix from allele profile")
    print(f"Locus count: {len(rq.loci)}")
    print(f"Profile count: {len(rq.profiles)}")

    validate_profiles(rq.loci, rq.profiles)
    print("Profiles validated")

    allele_mx_df = DataFrame.from_dict(rq.profiles, 'index', dtype=str)
    job_id = uuid.uuid4()
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
    dist_mx_df: DataFrame = await dist_mx_from_local_file(rq.file_name)
    return {
        "distance_matrix": dist_mx_df.to_dict(orient='tight')
        }

@app.post("/v1/distance_matrix/from_mongo_ids")
async def dmx_from_mongodb(rq: DMXFromMongoIsdRequest):
    """
    Return a distance matrix from allele profiles defined in MongoDB documents
    """
    try:
        mongo_cursor = await mongo_api.get_field_data(
            collection=rq.collection,
            path_elements=rq.path_elements,
            mongo_ids=rq.mongo_ids
        )
    except mongo.MongoAPIError as e:
        return {
        "error": str(e)
        }
    # try:
    #     allele_mx_df: DataFrame = await allele_mx_from_bifrost_mongo(mongo_cursor)
    # except StopIteration as e:
    #     return {
    #     "job_id": rq.id,
    #     "error": e
    #     }
    # dist_mx_df: DataFrame = await dist_mx_from_allele_df(allele_mx_df, rq.id)
    return {
        "job_id": rq.id,
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
