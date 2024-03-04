from os import getenv
import traceback
from datetime import datetime
from json import load
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from pandas import DataFrame

import calculations

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

@app.post("/v1/distance_calculation/from_cgmlst")
async def dmx_from_mongodb(rq: DMXFromMongoDBRequest, background_tasks: BackgroundTasks):
    """
    Run a distance calculation from selected cgMLST profiles in MongoDB
    """
    
    # Initialize DistanceCalculation object
    dc = calculations.DistanceCalculation(
            seq_collection=rq.collection,
            seqid_field_path=rq.seqid_field_path,
            profile_field_path=rq.profile_field_path,
            seq_mongo_ids=rq.mongo_ids,
            status='new',
            created_at=datetime.now(),
            finished_at=None,
            id=None
    )
    dc.id = dc.save()
    
    # Query MongoDB for the allele profiles
    try:
        profile_count, cursor = await dc.query_mongodb_for_allele_profiles()
    except calculations.MissingDataException as e:
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

@app.get("/v1/distance_calculation/status/")
async def dist_status(job_id: str):
    """
    Get job status of a distance calculation
    """

    dc = calculations.DistanceCalculation.find(job_id)
    
    return JSONResponse(
        content={
            'job_id': dc.id,
            'created_at': dc.created_at.isoformat(),
            'finished_at': dc.finished_at.isoformat(),
            'status': dc.status
        }
    )

@app.get("/v1/distance_calculation/result/")
async def dist_status(job_id: str):
    """
    Get result of a distance calculation
    """

    dc = calculations.DistanceCalculation.find(job_id)
    with open(Path(dc.folder, 'distance_matrix.json')) as f:
        distances = load(f)
    
    return JSONResponse(
        content={
            'job_id': dc.id,
            'distances': distances
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
