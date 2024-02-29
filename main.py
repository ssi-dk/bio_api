from os import getenv
import traceback
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from pandas import DataFrame

import mongo

from pydantic_classes import DMXFromMongoDBRequest, HCTreeCalcRequest
from tree_maker import make_tree

app = FastAPI()

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
DMX_DIR = getenv('DMX_DIR', '/dmx_data')

def timed_msg(msg: str):
    print(datetime.now().isoformat(), msg)

@app.get("/")
def root():
    return JSONResponse(content={"message": "Hello World"})

@app.post("/v1/distance_matrix/from_mongodb")
async def dmx_from_mongodb(rq: DMXFromMongoDBRequest, background_tasks: BackgroundTasks):
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
        return JSONResponse(
            status_code=422, # Unprocessable Content
            content={
                'job_id': dc.id,
                'message': str(e)
            }
        )

    # Initiate the calculation
    background_tasks.add_task(dc.calculate, cursor)

    return JSONResponse(
        status_code=202,  # Accepted
        content={
            'job_id': dc.id,
            'created_at': dc.created_at.isoformat(),
            'status': dc.status,
            'profile_count': profile_count,
        }
    )

@app.post("/v1/tree/hc/")
async def hc_tree(rq: HCTreeCalcRequest):
    content = {"method": rq.method}
    try:
        dist_df: DataFrame = DataFrame.from_dict(rq.distances, orient='index')
        tree = make_tree(dist_df, rq.method)
        content['tree'] = tree
    except ValueError as e:
        content['error'] = str(e)
        print(traceback.format_exc())
    return JSONResponse(content=content)
