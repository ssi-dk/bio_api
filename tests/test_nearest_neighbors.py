# test_nearest_neighbors.py

import pytest
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
import logging
from unittest.mock import patch
from calculations import NearestNeighbors, Calculation, MissingDataException
from .requirements import (
    MOCK_INPUT_SEQUENCE,
    MOCK_MONGO_CONFIG, 
    MOCK_INPUT_ID, 
    MOCK_NEIGHBOR_ID_missing
)
from .mongo_mock import MongoAPI, MongoConfig

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("nearest_neighbors_test.log", mode='w')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

@pytest.mark.asyncio
@patch("calculations.Config.get_section")
async def test_nearest_neighbors_creation_and_profile_retrieval(mock_get_section, prepared_mongo):
    ### CODE 200
    logger.info("===== test_nearest_neighbors_creation_and_profile_retrieval =====")

    mock_get_section.return_value = MOCK_MONGO_CONFIG

    calc = NearestNeighbors(
        input_mongo_id=str(MOCK_INPUT_ID),
        cutoff=MOCK_MONGO_CONFIG["cutoff"],
        filtering=MOCK_MONGO_CONFIG["filtering"],
        unknowns_are_diffs=MOCK_MONGO_CONFIG["unknowns_are_diffs"]
    )

    calc.input_sequence = await calc.query_mongodb_for_input_profile()
    logger.info(f"Input sequence retrieved: {calc.input_sequence}")

    assert calc.input_sequence["_id"] == MOCK_INPUT_ID
    assert "categories" in calc.input_sequence

    profile = calc.input_profile
    logger.info(f"Input profile hoisted: {profile}")

    assert profile[0] == 1
    assert profile[1] == 2



@pytest.mark.asyncio
@patch("calculations.Config.get_section")
async def test_bad_request_400(mock_get_section, mock_db):
    logger.info("===== test_bad_request_400 =====")
    mock_get_section.return_value = MOCK_MONGO_CONFIG
    mongo_api = MongoAPI(db=mock_db)
    Calculation.set_mongo_api(mongo_api)

    calc = NearestNeighbors(
        input_mongo_id="InvalidObjectID",  # This ID isn't in mock DB
        cutoff=MOCK_MONGO_CONFIG["cutoff"],
        filtering=MOCK_MONGO_CONFIG["filtering"],
        unknowns_are_diffs=MOCK_MONGO_CONFIG["unknowns_are_diffs"]
    )
    with pytest.raises(InvalidId):
        await calc.query_mongodb_for_input_profile()

@pytest.mark.asyncio
@patch("calculations.Config.get_section")
async def test_no_objectID_found_404(mock_get_section, mock_db):
    """Simulate how the FastAPI route would raise a 404 HTTPException."""
    logger.info("===== test_no_objectID_found_404 =====")

    mock_get_section.return_value = MOCK_MONGO_CONFIG
    mongo_api = MongoAPI(db=mock_db)
    Calculation.set_mongo_api(mongo_api)

    calc = NearestNeighbors(
        input_mongo_id=str(MOCK_NEIGHBOR_ID_missing),  # This ID isn't in mock DB
        cutoff=MOCK_MONGO_CONFIG["cutoff"],
        filtering=MOCK_MONGO_CONFIG["filtering"],
        unknowns_are_diffs=MOCK_MONGO_CONFIG["unknowns_are_diffs"]
    )
    with pytest.raises(MissingDataException):
        await calc.query_mongodb_for_input_profile()


@pytest.mark.asyncio
@patch("calculations.Config.get_section")
async def test_nearest_neighbors_calculate(mock_get_section, prepared_populated_mongo):
    ### CODE 200
    logger.info("===== test_nearest_neighbors_calculate =====")

    mock_get_section.return_value = MOCK_MONGO_CONFIG

    calc = NearestNeighbors(
        input_mongo_id=str(MOCK_INPUT_ID),
        cutoff=MOCK_MONGO_CONFIG["cutoff"],
        filtering=MOCK_MONGO_CONFIG["filtering"],
        unknowns_are_diffs=MOCK_MONGO_CONFIG["unknowns_are_diffs"]
    )
    try:
        calc.input_sequence = await calc.query_mongodb_for_input_profile()
    except MissingDataException:
        print(list(prepared_populated_mongo["samples"].find({})))
        raise
    logger.info(f"Input sequence retrieved: {calc.input_sequence}")

    assert calc.input_sequence["_id"] == MOCK_INPUT_ID
    assert "categories" in calc.input_sequence
    await calc.calculate()
    logger.info(f"Result: {calc.result}")
    assert len(calc.result) == 1

"""

app = FastAPI(
    title="Bio API", 
    description="REST API for controlling bioinformatic calculations", 
    version="0.2.0",
    root_path="/bioapi"

)

MONGO_CONNECTION_STRING = getenv('BIFROST_DB_KEY', 'mongodb://mongodb:27017/bio_api_test')

mongo_api = MongoAPI(MONGO_CONNECTION_STRING)
calculations.Calculation.set_mongo_api(mongo_api) -> #  set my fake api in 

Then call this:

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

Then make some asserts which test the different status codes

"""