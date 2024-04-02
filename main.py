from os import getenv
from datetime import datetime
from json import load
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from bson.errors import InvalidId

import calculations

from pydantic_classes import NearestNeighborsRequest,  DMXFromMongoRequest, HCTreeCalcFromDMXJobRequest

app = FastAPI(title="Bio API", description="REST API for controlling bioinformatic calculations", version="0.1.0")

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
DMX_DIR = getenv('DMX_DIR', '/dmx_data')

def timed_msg(msg: str):
    print(datetime.now().isoformat(), msg)

@app.get("/", tags=["Test"])
def root():
    return JSONResponse(content={"message": "Hello World"})

@app.post("/v1/nearest_neighbors", tags=["Nearest Neighbors"], status_code=202)
async def nearest_neighbors(rq: NearestNeighborsRequest, background_tasks: BackgroundTasks):
    nn = calculations.NearestNeighbors(
        seq_collection=rq.seq_collection,
        profile_field_path=rq.profile_field_path,
        input_mongo_id=rq.input_mongo_id,
        cutoff=rq.cutoff,
        unknowns_are_diffs=rq.unknowns_are_diffs
    )

    # Get input profile or fail if sequence not found
    try:
        # Add the input sequence to the nn object so we can run calculate() without arguments.
        # Note that the input sequence will not be stored as part of the nn object.
        nn.input_sequence = await nn.query_mongodb_for_input_profile()
    except InvalidId as e:
        return JSONResponse(
            status_code=400, # Bad Request
            content={
                'error': str(e)
            }
        )
    except calculations.MissingDataException as e:
        return JSONResponse(
            status_code=404, # Not found
            content={
                'error': str(e)
            }
        )

    # Check that at least the input sequence has the profile field, otherwise there's no reason to run the calculation
    if not nn.profile_field_path in nn.input_sequence:
        return JSONResponse(
            status_code=422, # Unprocessable content
            content={
                'error': f"Input sequence {nn.input_sequence['_id']} does not have a field named '{nn.profile_field_path}'."
            }
        )

    nn._id = await nn.insert_document()
    background_tasks.add_task(nn.calculate)

    return JSONResponse(
        status_code=202,
        content={
            'job_id': str(nn._id),
            'created_at': nn.created_at.isoformat(),
            'status': nn.status
        }
    )

@app.get("/v1/nearest_neighbors/{nn_id}", tags=["Nearest Neighbors"])
async def nn_result(nn_id: str, level:str='full'):
    """
    Get result of a nearest neighbors calculation
    """
    try:
        nn = calculations.NearestNeighbors.find(nn_id)
    except InvalidId as e:
        return JSONResponse(status_code=400, content={'error': str(e)})
    if nn is None:
        err_msg = f"A document with id {nn_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    
    content:dict = nn.to_dict()
    
    if level == 'full' and content['status'] != 'completed':
        content.pop['result']

    return JSONResponse(
        content=content
    )

@app.post("/v1/distance_calculations", tags=["Distances"], status_code=202)
async def dmx_from_mongodb(rq: DMXFromMongoRequest, background_tasks: BackgroundTasks):
    """
    Run a distance calculation from selected cgMLST profiles in MongoDB
    """
    
    # Initialize DistanceCalculation object
    dc = calculations.DistanceCalculation(
            seq_collection=rq.seq_collection,
            seqid_field_path=rq.seqid_field_path,
            profile_field_path=rq.profile_field_path,
            seq_mongo_ids=rq.mongo_ids,
            created_at=datetime.now(),
            finished_at=None,
    )
    
    # Query MongoDB for the allele profiles
    try:
        profile_count, cursor = await dc.query_mongodb_for_allele_profiles()
    except InvalidId as e:
        return JSONResponse(
            status_code=400, # Bad Request
            content={
                'error': str(e)
            }
        )
    except calculations.MissingDataException as e:
        return JSONResponse(
            status_code=422, # Unprocessable Content
            content={
                'message': str(e)
            }
        )

    dc._id = await dc.insert_document()
    background_tasks.add_task(dc.calculate, cursor)

    return JSONResponse(
        status_code=202,  # Accepted
        content={
            'job_id': str(dc._id),
            'created_at': dc.created_at.isoformat(),
            'status': dc.status,
            'profile_count': profile_count,
        }
    )

@app.get("/v1/distance_calculations/{dc_id}", tags=["Distances"])
async def dmx_result(dc_id: str, level:str='full'):
    """
    Get result of a distance calculation
    """
    try:
        dc = calculations.DistanceCalculation.find(dc_id)
    except InvalidId as e:
        return JSONResponse(status_code=400, content={'error': str(e)})
    if dc is None:
        err_msg = f"A document with id {dc_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})
    content = dc.to_dict()
    
    if dc.status == 'completed':
        content['finished_at'] = dc.finished_at.isoformat()
        if level == 'full':
            with open(Path(dc.folder, 'distance_matrix.json')) as f:
                content['result'] = load(f)

    return JSONResponse(
        content=content
    )

@app.post("/v1/trees", tags=["Trees"], status_code=202)
async def hc_tree_from_dmx_job(rq: HCTreeCalcFromDMXJobRequest, background_tasks: BackgroundTasks):
    dc = calculations.DistanceCalculation.find(rq.dmx_job)
    if dc is None:
        return JSONResponse(
            status_code=404,
            content={'error': f"Distance matrix job with id {rq.dmx_job} does not exist."}
        )
    if dc.status != 'completed':
        return JSONResponse(
            status_code=422,
            content={'error': f"Distance matrix job with id {rq.dmx_job} has status '{dc.status}'."}
        )
    tc = calculations.TreeCalculation(rq.dmx_job, rq.method)
    tc._id = await tc.insert_document()
    background_tasks.add_task(tc.calculate)
    return JSONResponse(
    status_code=202,  # Accepted
    content={
        'job_id': str(tc._id),
        'created_at': tc.created_at.isoformat(),
        'status': tc.status,
    }
)

@app.get("/v1/trees/{tc_id}", tags=["Trees"])
async def hc_tree_result(tc_id:str, level:str='full'):
    try:
        tc = calculations.TreeCalculation.find(tc_id)
    except InvalidId as e:
        return JSONResponse(status_code=400, content={'error': str(e)})
    if tc is None:
        err_msg = f"A document with id {tc_id} was not found in collection {calculations.DistanceCalculation.collection}."
        return JSONResponse(status_code=404, content={'error': err_msg})

    content = tc.to_dict()
    
    if level == 'full' and content['status'] != 'completed':
        content.pop('result')

    return JSONResponse(
        content=content
    )