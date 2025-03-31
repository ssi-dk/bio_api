# conftest.py

import pytest
import pytest_asyncio
import mongomock
import asyncio
from unittest.mock import AsyncMock, patch
import uuid
from bson import ObjectId
from aio_pika.exceptions import AMQPConnectionError
from . import requirements

# --- MongoDB Fixture --- #

@pytest.fixture
def mock_db():
    """Creates an in-memory MongoDB instance"""
    client = mongomock.MongoClient()
    return client["testdb"]

# --- RabbitMQ Fixtures --- #

class MockSOFIMessenger:
    """A mock version of SOFIMessenger for test simulation."""
    def __init__(self, amqp_url):
        self.amqp_url = amqp_url
        self.send_hpc_call = AsyncMock()
        self._responses = asyncio.Queue()

    async def consume(self):
        """Simulated async generator returning one fake response"""
        response = {
            "status": "success",
            "job_uuid": uuid.uuid4().hex
        }
        yield response

@pytest.fixture
def mock_messenger():
    """Provides a mocked SOFIMessenger instance"""
    return MockSOFIMessenger("amqp://guest:guest@rabbitmq/")

@pytest_asyncio.fixture
async def mock_successful_rabbitmq_connection():
    """Mocks a successful aio_pika.connect_robust call"""
    with patch("aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        yield mock_connect

@pytest_asyncio.fixture
async def mock_failed_rabbitmq_connection():
    """Mocks a failed aio_pika.connect_robust call with retries"""
    from aio_pika.exceptions import AMQPConnectionError

    with patch("aio_pika.connect_robust", side_effect=AMQPConnectionError) as mock_connect, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        yield mock_connect, mock_sleep

@pytest.fixture
def prepopulated_mock_db(mock_db):
    # Insert input sequence
    mock_db["samples"].insert_one(requirements.MOCK_INPUT_SEQUENCE)
    mock_db["samples"].insert_one(requirements.MOCK_NEIGHBOR_SEQUENCE)
    mock_db["BioAPI_config"].insert_one(dict(requirements.MOCK_MONGO_CONFIG, section="nearest_neighbors"))
    return mock_db

@pytest.fixture
def fully_mocked_mongo(mock_db):
    """
    Prepopulate mock MongoDB with input and neighbor sequences + config.
    """
    mock_db["samples"].insert_one(requirements.MOCK_INPUT_SEQUENCE)
    mock_db["samples"].insert_one(requirements.MOCK_NEIGHBOR_SEQUENCE)
    mock_db["samples"].insert_one(requirements.MOCK_NEIGHBOR_SEQUENCE_2)

    mock_config = dict(requirements.MOCK_MONGO_CONFIG)
    mock_config["section"] = "nearest_neighbors"
    mock_db["BioAPI_config"].insert_one(mock_config)

    return mock_db
