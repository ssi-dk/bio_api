from os import getenv
import traceback
from datetime import datetime
from json import load
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from pandas import DataFrame
from bson.errors import InvalidId

import calculations

from pydantic_classes import DMXFromMongoRequest, HCTreeCalcRequest
from tree_maker import make_tree

app = FastAPI(title="Bio API", description="REST API for controlling bioinformatic calculations", version="0.1.0")

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
DMX_DIR = getenv('DMX_DIR', '/dmx_data')

def timed_msg(msg: str):
    print(datetime.now().isoformat(), msg)

@app.get("/", tags=["Test"])
def root():
    return JSONResponse(content={"message": "Hello World"})

@app.post("/v1/distance_calculation/from_cgmlst", tags=["cgMLST"])
async def dmx_from_mongodb(rq: DMXFromMongoRequest, background_tasks: BackgroundTasks):
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
    dc.id = await dc.save()
    
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

@app.get("/v1/distance_calculation/status/", tags=["cgMLST"])
async def dist_status(job_id: str):
    """
    Get job status of a distance calculation
    """
    try:
        dc = calculations.DistanceCalculation.find(job_id)
    except InvalidId as e:
        return JSONResponse(status_code=422, content={'error': str(e)})
    if dc is None:
        err_msg = f"A document with id {job_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    return JSONResponse(
        content={
            'job_id': dc.id,
            'created_at': dc.created_at.isoformat(),
            'finished_at': dc.finished_at.isoformat(),
            'status': dc.status
        }
    )

@app.get("/v1/distance_calculation/result/", tags=["cgMLST"])
async def dist_status(job_id: str):
    """
    Get result of a distance calculation
    """
    try:
        dc = calculations.DistanceCalculation.find(job_id)
    except InvalidId as e:
        return JSONResponse(status_code=422, content={'error': str(e)})
    if dc is None:
        err_msg = f"A document with id {job_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    with open(Path(dc.folder, 'distance_matrix.json')) as f:
        distances = load(f)
    return JSONResponse(
        content={
            'job_id': dc.id,
            'distances': distances
        }
    )

@app.post("/v1/hc_tree/from_request/", tags=["cgMLST"])
async def hc_tree_from_rq(rq: HCTreeCalcRequest):
    content = {"method": rq.method}
    try:
        dist_df: DataFrame = DataFrame.from_dict(rq.distances, orient='index')
        tree = make_tree(dist_df, rq.method)
        content['tree'] = tree
    except ValueError as e:
        content['error'] = str(e)
        print(traceback.format_exc())
    return JSONResponse(content=content)

@app.get("/v1/hc_tree/from_dmx_job/", tags=["cgMLST"])
async def hc_tree_from_dmx_job(dmx_job:str, method:str, background_tasks: BackgroundTasks):
    tc = calculations.TreeCalculation(dmx_job, method)
    tc.id = await tc.save()
    background_tasks.add_task(tc.calculate)
    return JSONResponse(
    status_code=202,  # Accepted
    content={
        'job_id': tc.id,
        'created_at': tc.created_at.isoformat(),
        'status': tc.status,
    }
)

@app.get("/v1/hc_tree/status/", tags=["cgMLST"])
async def hc_tree_status(job_id:str):
    try:
        tc = calculations.TreeCalculation.find(job_id)
    except InvalidId as e:
        return JSONResponse(status_code=422, content={'error': str(e)})
    if tc is None:
        err_msg = f"A document with id {job_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    return JSONResponse(
        content={
            'job_id': tc.id,
            'created_at': tc.created_at.isoformat(),
            'finished_at': tc.finished_at.isoformat(),
            'status': tc.status
        }
    )

@app.get("/v1/hc_tree/result/", tags=["cgMLST"])
async def hc_tree_result(job_id:str):
    try:
        tc = calculations.TreeCalculation.find(job_id)
    except InvalidId as e:
        return JSONResponse(status_code=422, content={'error': str(e)})
    if tc is None:
        err_msg = f"A document with id {job_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    tree = await tc.get_tree()
    return JSONResponse(
        content={
            'job_id': tc.id,
            'created_at': tc.created_at.isoformat(),
            'finished_at': tc.finished_at.isoformat(),
            'status': tc.status,
            'tree': tree
        }
    )