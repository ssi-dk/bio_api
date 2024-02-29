from os import getenv
import uuid
from typing import Union
from io import StringIO
from pathlib import Path
import traceback
import asyncio
from datetime import datetime

from pydantic import BaseModel
from fastapi import FastAPI
from pandas import DataFrame, read_table
from pymongo.errors import DocumentTooLarge

import mongo

from pydantic_classes import DMXFromLocalFileRequest, DMXFromMongoDBRequest, DMXFromProfilesRequest, HCTreeCalcRequest
from tree_maker import make_tree
# from qstat import consume_qstat

app = FastAPI()

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
DMX_DIR = getenv('DMX_DIR', '/dmx_data')

def timed_msg(msg: str):
    print(datetime.now().isoformat(), msg)

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

async def allele_df_from_mongodb_cursor(cursor, seqid_field_path: str, profile_field_path: str):
    # Generate an allele matrix with all the allele profiles from the mongo cursor.

    full_dict = dict()

    try:
        while True:
            mongo_item = next(cursor)
            sequence_id = mongo.hoist(mongo_item, seqid_field_path)
            allele_profile = mongo.hoist(mongo_item, profile_field_path)
            full_dict[sequence_id] = allele_profile
    except StopIteration:
        pass

    df = DataFrame.from_dict(full_dict, 'index', dtype=str)
    return df

async def dist_mx_from_allele_df(allele_mx:DataFrame, job_id: str):
    # save allele matrix to a file that cgmlst-dists can use for input
    allele_mx_filepath = Path(DMX_DIR, f'allele_matrix_{job_id}.tsv')
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

@app.post("/v1/distance_matrix/from_local_file")
async def dmx_from_local_file(rq: DMXFromLocalFileRequest):
    """
    Return a distance matrix from allele profiles defined in a local tsv file in the Bio API container
    """
    job_id, created_at = await mongo.mongo_api.create_dmx_job()
    dist_mx_df: DataFrame = await calculate_dmx_from_file(rq.file_path)
    dist_mx_dict = dist_mx_df.to_dict(orient='index')
    finished_at = await mongo.mongo_api.mark_job_as_finished(job_id)
    status = "calculation_completed"
    try:
        await mongo.mongo_api.write_result_to_job(job_id, dist_mx_dict)
        status = "saved_to_mongodb"
    except DocumentTooLarge:
        status = "document_too_large"
        print(f"Job {job_id}: result too large for saving in MongoDB! Will save as Parquet file as plan B.")
        dist_mx_df.to_parquet(path=f'/data/{job_id}.parquet')
    return {
        'job_id': job_id,
        'created_at': created_at,
        'finished_at': finished_at,
        'distance_matrix': dist_mx_dict,
        'status': status
        }

@app.post("/v1/distance_matrix/from_request")
async def dmx_from_request(rq: DMXFromProfilesRequest):
    """
    Return a distance matrix from allele profiles that are included directly in the request
    """
    job_id, created_at = await mongo.mongo_api.create_dmx_job()

    print("Requested distance matrix from allele profile")
    print(f"Locus count: {len(rq.loci)}")
    print(f"Profile count: {len(rq.profiles)}")

    validate_profiles(rq.loci, rq.profiles)
    print("Profiles validated")

    allele_mx_df = DataFrame.from_dict(rq.profiles, 'index', dtype=str)
    dist_mx_df: DataFrame = await dist_mx_from_allele_df(allele_mx_df, job_id)
    dist_mx_dict = dist_mx_df.to_dict(orient='index')
    finished_at = await mongo.mongo_api.mark_job_as_finished(job_id)
    return {
        'job_id': job_id,
        'created_at': created_at,
        'finished_at': finished_at,
        'distance_matrix': dist_mx_dict
        }

@app.post("/v1/distance_matrix/from_mongodb")
async def dmx_from_mongodb(rq: DMXFromMongoDBRequest):
    """
    Return a distance matrix from allele profiles defined in MongoDB documents
    """
    
    # Initialize DistanceCalculation object
    dc = mongo.DistanceCalculation(
            seq_collection=rq.collection,
            seqid_field_path=rq.seqid_field_path,
            profile_field_path=rq.profile_field_path,
            seq_mongo_ids=rq.mongo_ids
    )
    
    # Query MongoDB for the allele profiles
    try:
        profile_count, cursor = await dc.query_mongodb_for_allele_profiles()
    except mongo.MissingDataException as e:
        return {
            'status': 'error',
            'error_msg:': str(e)
        }

    # Compile allele matrix from sequence documents
    allele_mx_df: DataFrame = await dc.amx_df_from_mongodb_cursor(cursor)
    
    # Save allele mx as tsv file in job folder
    await dc.save_amx_df_as_tsv(allele_mx_df)

    # Calculate distance matrix
    dist_mx_df: DataFrame = await dc.dmx_df_from_amx_tsv()

    # Save distance matrix as JSON
    dist_mx_dict = dist_mx_df.to_dict(orient='index')
    await dc.save_dmx_as_json(dist_mx_dict)

    # Mark job as finished
    dc.finished_at = await dc.mark_as_finished()

    return {
        'dmx_job_id': dc.id,
        'created_at': dc.created_at,
        'finished_at': dc.finished_at,
        'profile_count': profile_count,
        }

@app.post("/v1/tree/hc/")
async def hc_tree(rq: HCTreeCalcRequest):
    response = {"method": rq.method}
    try:
        dist_df: DataFrame = DataFrame.from_dict(rq.distances, orient='index')
        tree = make_tree(dist_df, rq.method)
        response['tree'] = tree
    except ValueError as e:
        response['error'] = str(e)
        print(traceback.format_exc())
    return response
