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

@app.get("/")
def root():
    return {"message": "Hello World"}

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
