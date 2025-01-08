from os import getenv
from datetime import datetime
from json import load
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from bson.errors import InvalidId

import calculations

import pydantic_classes as pc

app = FastAPI(title="Bio API", description="REST API for controlling bioinformatic calculations", version="0.2.0")

MANUAL_MX_DIR = getenv('BIO_API_TEST_INPUT_DIR', '/test_input')
DMX_DIR = getenv('DMX_DIR', '/dmx_data')

# standardize the error responses
additional_responses = {
    400: {"model": pc.Message}, #Bad Request (invalid input).
    404: {"model": pc.Message} #Not Found (missing resource).
    }

#SOFI code working as a browser (client) calls the URL within app.post to start a NN job

@app.post("/v1/nearest_neighbors", #registers when client sends a data or request its handled by nearest_neighbors function
    tags=["Nearest Neighbors"], 
    status_code=201, # succesfull creating the nearest_neighbors job
    response_model=pc.CommonPOSTResponse, #response of the pydantic class (pc) -> see further down, like job_id, created_at, status
    responses=additional_responses # errors 400,404 or additional definitions
    )



async def nearest_neighbors(rq: pc.NearestNeighborsRequest, background_tasks: BackgroundTasks):
    # rq is the parameters SOFI sends with the call
    # background_tasks - SOFI can send the HTTP responds and then do calculatiosn as a background as opposed to task and then responds
    #  SOFI can make several calculations without waiting for the others
    # instanciate the calculate class

    """
    rq: pc.NearestNeighborsReques -> the structure of the request (in a json format??) should fit with that of 
        NearestNeighborsRequest defined in the pydantic_classes.py -> request passes validation, FastAPI calls the nearest_neighbors function
    """
    calc = calculations.NearestNeighbors(
        seq_collection=rq.seq_collection,
        filtering = rq.filtering,
        profile_field_path=rq.profile_field_path,
        input_mongo_id=rq.input_mongo_id,
        cutoff=rq.cutoff,
        unknowns_are_diffs=rq.unknowns_are_diffs
    )

    # Get input profile or fail if sequence not found
    try:
        # Add the input sequence to the nn object so we can run calculate() without arguments.
        # Note that the input sequence will not be stored as part of the nn object.
        calc.input_sequence = await calc.query_mongodb_for_input_profile()
    except InvalidId as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
            )
    except calculations.MissingDataException as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
            )

    # Check that at least the input sequence has the profile field, otherwise there's no reason to run the calculation
    try:
        _p = calc.input_profile
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Input sequence {calc.input_sequence['_id']} does not have a field named '{calc.profile_field_path}'."
            )
    
    calc._id = await calc.insert_document() # we cannot add this to background, as we need ID before sending a responds
    
    background_tasks.add_task(calc.calculate) #FASTAPI add task (calculation) to background - e.g. calc.calculate 

    return pc.CommonPOSTResponse(
        job_id=str(calc._id), #we need a job ID when we send a responds for the client
        created_at=calc.created_at.isoformat(),
        status=calc.status
    )

#once a caluclation has inititated - SOFI needs to extract the calculation with nn_id which is know once the request has been made
# SOFI uses a loop and every 2nd second "ask what is the status with job nn_id" 
@app.get("/v1/nearest_neighbors/{nn_id}",
    tags=["Nearest Neighbors"],
    response_model=pc.NearestNeighborsGETResponse,
    responses=additional_responses
    )
async def nn_result(nn_id: str, level:str='full'):
    """
    Get result of a nearest neighbors calculation
    """
    try:
        calc = calculations.NearestNeighbors.find(nn_id)
    except InvalidId as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
            )
    if calc is None:
        raise HTTPException(
            status_code=400,
            detail=f"A document with id {nn_id} was not found in collection {calculations.DistanceCalculation.collection}."
            )

    content:dict = calc.to_dict()
    
    # level : 'full' responds gives both status and results (e.g distance matrix)
    # level : 'basic' bioAPI will only return status and not result
    # level is specified by client depending on the amount of information they need
    if level != 'full' and content['status'] == 'completed':
        content['result'] = None

    return pc.NearestNeighborsGETResponse(**content)

#use post to 'order' calculation and get 'to extract' calculation result
@app.post("/v1/distance_calculations",
    response_model=pc.CommonPOSTResponse,
    tags=["Distances"],
    status_code=201,
    responses=additional_responses
    )
async def dmx_from_mongodb(rq: pc.DistanceMatrixRequest, background_tasks: BackgroundTasks):
    """
    Run a distance calculation from selected cgMLST profiles in MongoDB
    """
    
    # Initialize DistanceCalculation object
    calc = calculations.DistanceCalculation(
            seq_collection=rq.seq_collection,
            seqid_field_path=rq.seqid_field_path,
            profile_field_path=rq.profile_field_path,
            seq_mongo_ids=rq.seq_mongo_ids,
            created_at=datetime.now(),
            finished_at=None,
    )
    
    # Query MongoDB for the allele profiles
    try:
        _profile_count, cursor = await calc.query_mongodb_for_allele_profiles()
    except InvalidId as e:
        return HTTPException(
            status_code=400, # Bad Request
           detail=str(e)
        )
    except calculations.MissingDataException as e:
        raise HTTPException(
            status_code=404,
            detail=str(e)
            )

    calc._id = await calc.insert_document()
    background_tasks.add_task(calc.calculate, cursor)

    return pc.CommonPOSTResponse(
        job_id=str(calc._id),
        created_at=calc.created_at.isoformat(),
        status=calc.status
    )

@app.get("/v1/distance_calculations/{dc_id}",
    tags=["Distances"],
    response_model=pc.DistanceMatrixGETResponse,
    responses=additional_responses
)
async def dmx_result(dc_id: str, level:str='full'):
    """
    Get result of a distance calculation
    """
    try:
        calc = calculations.DistanceCalculation.find(dc_id)
    except InvalidId as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
            )

    if calc is None:
        raise HTTPException(
            status_code=404,
            detail=f"A document with id {dc_id} was not found in collection {calculations.DistanceCalculation.collection}."
            )

    content = calc.to_dict()
    
    if calc.status == 'completed':

        # Replace ObjectId's with str
        for k, v in content['result']['seq_to_mongo'].items():
            content['result']['seq_to_mongo'][k] = str(v)

        content['finished_at'] = calc.finished_at.isoformat()
        content['result'] = calc.result
        if level == 'full':
            # Add result from file
            with open(Path(calc.folder, calculations.DistanceCalculation.get_dist_mx_filename())) as f:
                distances = f.read()
            print("This is what the distance matrix looks like:")
            print(distances)
            content['result']['distances'] = distances

    return pc.DistanceMatrixGETResponse(**content)

@app.post("/v1/trees",
    response_model=pc.CommonPOSTResponse,
    tags=["Trees"],
    status_code=201,
    responses=additional_responses
    )
async def hc_tree_from_dmx_job(rq: pc.HCTreeCalcRequest, background_tasks: BackgroundTasks):
    calc = calculations.DistanceCalculation.find(rq.dmx_job)
    if calc is None:
        return HTTPException(
            status_code=404,
            content={'error': f"Distance matrix job with id {rq.dmx_job} does not exist."}
        )
    if calc.status != 'completed':
        raise HTTPException(
            status_code=400,
            detail=str(f"Distance matrix job with id {rq.dmx_job} has status '{calc.status}'.")
            )
    tc = calculations.TreeCalculation(rq.dmx_job, rq.method)
    tc._id = await tc.insert_document()
    background_tasks.add_task(tc.calculate)
    return pc.CommonPOSTResponse(
        job_id=str(tc._id),
        created_at=tc.created_at.isoformat(),
        status=tc.status
)

@app.get("/v1/trees/{tc_id}",
    tags=["Trees"],
    response_model=pc.HCTreeCalcGETResponse,
    responses=additional_responses
    )
async def hc_tree_result(tc_id:str, level:str='full'):
    try:
        calc = calculations.TreeCalculation.find(tc_id)
    except InvalidId as e:
        return HTTPException(status_code=400, detail=str(e))
    if calc is None:
        return HTTPException(
            status_code=404,
            detail=f"A document with id {tc_id} was not found in collection {calculations.DistanceCalculation.collection}.")

    content = calc.to_dict()
    if level != 'full' and content['status'] == 'completed':
        content['result'] = None

    return pc.HCTreeCalcGETResponse(**content)