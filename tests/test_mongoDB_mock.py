import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
import mongomock
import pymongo
import json
import os
import logging
from bson import ObjectId, json_util
from .requirements import MOCK_INPUT_SEQUENCE, MOCK_MONGO_CONFIG, MOCK_INPUT_ID
from .mongo_mock import MongoAPI, MongoConfig

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("mongoDB_mock.log", mode='w')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# --- Test: Insert Logic ---

def test_sequence_insertion(mock_db):
    """Test that insert_one returns an boolean value for succesful insertion"""
    logger.info("===== test_sequence_insertion =====")

    mongoapi = MongoAPI(db=mock_db)
    collection = mongoapi.db["samples"]
    result = collection.insert_one(MOCK_INPUT_SEQUENCE)
    logger.info(f"Insertion result: acknowledged={result.acknowledged}")
    assert result.acknowledged is True
    assert result.inserted_id == MOCK_INPUT_ID

def test_sequence_retrival(mock_db):
    """Test that an inserted sequence document can be retrieved"""
    logger.info("===== test_sequence_retrival =====")
    
    mongoapi = MongoAPI(db=mock_db)
    collection = mongoapi.db["samples"]
    collection.insert_one(MOCK_INPUT_SEQUENCE)

    result = collection.find_one({"_id": MOCK_INPUT_ID})
    logger.info(f"Retrieved document: {result}")
    assert result is not None
    assert result["categories"]["cgmlst"]["report"]["alleles"]["locus1"] == "1"

# --- Test: Config Set & Update ---

def test_config_section_set(mock_db):
    """Test that a config section can be inserted """
    logger.info("===== test_config_section_set =====")

    mongoapi = MongoAPI(db=mock_db)
    config = MongoConfig(mongoapi)

    doc = MOCK_MONGO_CONFIG.copy()
    doc["section"] = "test_section_set"
    result = config.set_section("test_section_set", doc)

    logger.info(f"Set config: {doc}, acknowledged: {result.acknowledged}")
    assert result.acknowledged is True

def test_config_update(mock_db):
    """Test that an existing config section can be updated"""
    logger.info("===== test_config_update =====")

    mongoapi = MongoAPI(db=mock_db)
    config = MongoConfig(mongoapi)

    section_name = "update_section"
    config.set_section(section_name, {"section": section_name, "cutoff": 1})
    before = config.get_section(section_name)
    logger.info(f"Before update cutoff: {before['cutoff']}")

    config.set_section(section_name, {"section": section_name, "cutoff": 5})
    after = config.get_section(section_name)
    logger.info(f"After update cutoff: {after['cutoff']}")
    assert after["cutoff"] == 5

# --- Test: Config Retrieval ---

def test_retrieve_config_section(mock_db):
    """Test that an inserted config section can be retrieved"""
    logger.info("===== test_retrieve_config_section =====")

    mongoapi = MongoAPI(db=mock_db)
    config = MongoConfig(mongoapi)

    doc = MOCK_MONGO_CONFIG.copy()
    doc["section"] = "test_section_get"
    mongoapi.db["BioAPI_config"].insert_one(doc)

    result = config.get_section("test_section_get")
    logger.info(f"Retrieved config: {result}")
    assert result["cutoff"] == doc["cutoff"]

def test_retrieve_nonexisting_config_section(mock_db):
    """Test retrieving a non-existing config section"""
    logger.info("===== test_retrieve_nonexisting_config_section =====")
    
    mongoapi = MongoAPI(db=mock_db)
    config = MongoConfig(mongoapi)

    result = config.get_section("nonexistent_section")
    assert result is None

# --- Test: Bulk Insert ---

def test_bulk_insert_config_sections(mock_db):
    """Test that multiple config sections can be inserted in bulk"""
    logger.info("===== test_bulk_insert_config_sections =====")

    mongoapi = MongoAPI(db=mock_db)
    config = MongoConfig(mongoapi)

    docs = [
        {"section": "multi1", "cutoff": 1},
        {"section": "multi2", "cutoff": 2}
    ]
    config.load(docs)

    count = mongoapi.db["BioAPI_config"].count_documents({})
    logger.info(f"Bulk inserted config count: {count}")
    assert count == 2

# --- Test: JSON Export ---

def test_export_sequence_collection_to_json(mock_db):
    """Test exporting the 'sequences' collection to a JSON file"""
    logger.info("===== test_export_sequence_collection_to_json =====")

    mongoapi = MongoAPI(db=mock_db)
    collection = mongoapi.db["samples"]

    collection.insert_one(MOCK_INPUT_SEQUENCE)
    docs = list(collection.find({}))

    with open("mocked_collection.json", "w") as file:
        json.dump(docs, file, default=json_util.default, indent=4)

    assert os.path.exists("mocked_collection.json")

    with open("mocked_collection.json") as f:
        exported_data = json.load(f)
        assert exported_data[0]["categories"]["cgmlst"]["report"]["alleles"]["locus1"] == "1"


# --- Test: Async Field Projection ---

@pytest.mark.asyncio
async def test_get_field_data_projection_for_specific_id(mock_db):
    """Test field projection using a specific Mongo ID"""
    logger.info("===== test_get_field_data_projection_for_specific_id =====")

    mongoapi = MongoAPI(db=mock_db)
    mongoapi.db["samples"].insert_one(MOCK_INPUT_SEQUENCE)

    count, cursor = await mongoapi.get_field_data(
        collection="samples",
        mongo_ids=[str(MOCK_INPUT_ID)],
        field_paths=["categories.cgmlst.report.alleles"]
    )
    docs = list(cursor)
    assert count == 1
    assert docs[0]["categories"]["cgmlst"]["report"]["alleles"]["locus1"] == "1"

@pytest.mark.asyncio
async def test_get_field_data_projection_all_documents(mock_db):
    """Test field projection across all documents without filter"""
    logger.info("===== test_get_field_data_projection_all_documents =====")

    mongoapi = MongoAPI(db=mock_db)
    mongoapi.db["samples"].insert_one(MOCK_INPUT_SEQUENCE)

    count, cursor = await mongoapi.get_field_data(
        collection="samples",
        mongo_ids=None,
        field_paths=["categories.cgmlst.report.alleles"]
    )
    docs = list(cursor)
    assert count == 1
    assert docs[0]["categories"]["cgmlst"]["report"]["alleles"]["locus1"] == "1"
