# test_nearest_neighbors.py

import pytest
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException
from unittest.mock import patch
from calculations import NearestNeighbors, Calculation
from .requirements import MOCK_INPUT_SEQUENCE, MOCK_MONGO_CONFIG, MOCK_INPUT_ID
from .mongo_mock import MongoAPI, MongoConfig

@pytest.mark.asyncio
@patch("calculations.Config.get_section")
async def test_nearest_neighbors_creation_and_profile_retrieval(mock_get_section, mock_db):
    # Step 1: Create mock mongo API with fully mocked DB
    mongo_api = MongoAPI(db=mock_db)
    Calculation.set_mongo_api(mongo_api)

    # Step 2: Return MOCK_MONGO_CONFIG when config.get_section is called
    mock_get_section.return_value = MOCK_MONGO_CONFIG

    # Step 3: Insert mock input sequence into mocked DB
    mock_db["samples"].insert_one(MOCK_INPUT_SEQUENCE)
    
    # Step 4: Create a NearestNeighbors object
    calc = NearestNeighbors(
        input_mongo_id=str(MOCK_INPUT_ID),
        cutoff=MOCK_MONGO_CONFIG["cutoff"],
        filtering=MOCK_MONGO_CONFIG["filtering"],
        unknowns_are_diffs=MOCK_MONGO_CONFIG["unknowns_are_diffs"]
    )

    # Step 5: Inject mock input sequence and call profile retrieval
    calc.input_sequence = await calc.query_mongodb_for_input_profile()

    # Step 6: Assert correctness
    assert calc.input_sequence["_id"] == MOCK_INPUT_ID
    assert "categories" in calc.input_sequence
    assert calc.input_mongo_id == str(MOCK_INPUT_ID)

    # Step 7: Test hoisting
    profile = calc.input_profile
    assert profile["locus1"] == "1"
    assert profile["locus2"] == "2"

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