from os import getenv
from datetime import datetime
from json import load
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from bson.errors import InvalidId

from mongo import MongoAPI
import calculations

import pydantic_classes as pc

app = FastAPI(
    title="Bio API", 
    description="REST API for controlling bioinformatic calculations", 
    version="0.2.0",
    root_path="/bioapi"

)

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')

mongo_api = MongoAPI(MONGO_CONNECTION_STRING)
calculations.Calculation.set_mongo_api(mongo_api)

DMX_DIR = getenv('DMX_DIR', '/dmx_data')

additional_responses = {
    400: {"model": pc.Message},
    404: {"model": pc.Message}
    }

@app.post("/v1/nearest_neighbors",
    tags=["Nearest Neighbors"],
    status_code=201,
    response_model=pc.CommonPOSTResponse,
    responses=additional_responses
    )
async def nearest_neighbors(rq: pc.NearestNeighborsRequest, background_tasks: BackgroundTasks):
    # Load defaults from Config if rq.cutoff, rq.filtering, or rq.unknowns_are_diffs are not provided -> defined in mongo.py 
    # self.collection_name = "BioAPI_config"
    
    #config_values = mongo_api.db['BioAPI_config'].find_one({'section': 'nearest_neighbors'}) or {}
    #cutoff=rq.cutoff if rq.cutoff is not None else config_values.get("cutoff"),
    #filtering=rq.filtering if rq.filtering is not None else config_values.get("filtering", {}),
    #unknowns_are_diffs=rq.unknowns_are_diffs if rq.unknowns_are_diffs is not None else config_values.get("unknowns_are_diffs")
    
    calc = calculations.NearestNeighbors(
        input_mongo_id=rq.input_mongo_id,
        cutoff=rq.cutoff,
        filtering=rq.filtering,
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
            detail=f"Input sequence {calc.input_sequence['_id']} does not have a field named '{calc.allele_path}'."
            )
    calc._id = await calc.insert_document()
    background_tasks.add_task(calc.calculate)

    return pc.CommonPOSTResponse(
        job_id=str(calc._id),
        created_at=calc.created_at.isoformat(),
        status=calc.status
    )

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
        calc = calculations.NearestNeighbors.recall(nn_id)
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

    print("Get nearest neighbors result.")
    calc.remove_filtered_pairs_from_self()
    content:dict = calc.to_dict()
    
    if level != 'full' and content['status'] == 'completed':
        content['result'] = None

    return pc.NearestNeighborsGETResponse(**content)

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
            seq_mongo_ids=rq.seq_mongo_ids,
    )

    #i dont think the created_at and finished_at here is necessary - they are in Calculation __init__
    #created_at=datetime.now(),
    #finished_at=None,

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
        calc = calculations.DistanceCalculation.recall(dc_id)
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
            with open(Path(calc.folder, 'distance_matrix.json')) as f:
                json = load(f)
                content['result']['distances'] = [calc.dmx_tsv_from_dict(json)]

    return pc.DistanceMatrixGETResponse(**content)

@app.post("/v1/trees",
    response_model=pc.CommonPOSTResponse,
    tags=["Trees"],
    status_code=201,
    responses=additional_responses
    )
async def hc_tree_from_dmx_job(rq: pc.HCTreeCalcRequest, background_tasks: BackgroundTasks):
    calc = calculations.DistanceCalculation.recall(rq.dmx_job)
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
        calc = calculations.TreeCalculation.recall(tc_id)
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

@app.post("/v1/snp_calculations",
    response_model=pc.CommonPOSTResponse,
    tags=["SNP"],
    status_code=201,
    responses=additional_responses
    )
async def snp(rq: pc.SNPRequest):
    """
    Initialize a new SNP calculation
    """

    # After - Load from config if not provided
    #config_values = mongo_api.db['BioAPI_config'].find_one({'section': 'snp'}) or {}
    #depth=rq.depth if rq.depth is not None else config_values.get("depth"),
    #ignore_hz=rq.ignore_hz if rq.ignore_hz is not None else config_values.get("ignore_hz"),
    #hpc_resources=rq.hpc_resources if rq.hpc_resources is not None else config_values.get("hpc_resources", {})
    
    calc = calculations.SNPCalculation(
        seq_mongo_ids=rq.seq_mongo_ids,
        reference_mongo_id=rq.reference_mongo_id,
        depth=rq.depth,
        ignore_hz=rq.ignore_hz,
        hpc_resources=rq.hpc_resources
    )


    # Save object in MongoDB, so at least we have something even if filename lookup fails
    await calc.insert_document()

    # First we need to get the files from a MongoDB lookup
    # calc.query_mongodb_for_file_names()

    # Now we are ready to send the calculation to RabbitMQ