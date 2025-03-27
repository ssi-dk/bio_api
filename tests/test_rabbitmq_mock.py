import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, patch
import aio_pika
import logging
from aio_pika.exceptions import AMQPConnectionError

# --- Logging Setup ---
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

file_handler = logging.FileHandler("RabbitMQ_mock.log", mode='w')
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# --- Mock Class ---
class MockSOFIMessenger:
    """A mock version of SOFIMessenger for test simulation."""

    def __init__(self, amqp_url):
        self.amqp_url = amqp_url
        self.send_hpc_call = AsyncMock()
        self._responses = asyncio.Queue()

    async def consume(self):
        # Simulate an async generator yielding a response
        response = {
            "status": "success",
            "job_uuid": uuid.uuid4().hex
        }
        yield response

# --- Tests ---
@pytest.mark.asyncio
async def test_mock_rabbitmq_connect_success():
    """Mock successful RabbitMQ connection"""
    logger.info("===== test_mock_rabbitmq_connect_success =====")
    
    with patch("aio_pika.connect_robust", new_callable=AsyncMock) as mock_connect:
        connection = await mock_connect("amqp://guest:guest@rabbitmq/")
        logger.info("Mocked RabbitMQ connection established.")
        assert connection is not None
        mock_connect.assert_called_once()

@pytest.mark.asyncio
async def test_mock_rabbitmq_connect_failure():
    """Simulate RabbitMQ connection failure (mocked)."""
    logger.info("===== test_mock_rabbitmq_connect_failure =====")

    with patch("aio_pika.connect_robust", side_effect=AMQPConnectionError) as mock_connect, \
         patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        
        tries = 3
        for i in range(tries):
            try:
                await aio_pika.connect_robust("amqp://guest:guest@rabbitmq/")
            except AMQPConnectionError:
                logger.info(f"Connection attempt {i+1} failed. Retrying...")
                await asyncio.sleep(1)
        
        assert mock_connect.call_count == tries
        assert mock_sleep.call_count == tries
        logger.info("All retries attempted and succefully failed.")


@pytest.mark.asyncio
async def test_mock_send_hpc_call():
    """Simulate sending a message to RabbitMQ via mocked SOFIMessenger."""
    logger.info("===== test_mock_send_hpc_call =====")
    messenger = MockSOFIMessenger("amqp://guest:guest@rabbitmq/")
    job_uuid = uuid.uuid4().hex
    hpc_payload = {
        "args": ["-h"],
        "cpus": 1,
        "memGB": 4,
        "group": "fvst_ssi",
        "nodes": "????"
    }

    await messenger.send_hpc_call(uuid=job_uuid, job_type="snp", args=hpc_payload)

    messenger.send_hpc_call.assert_called_once_with(
        uuid=job_uuid,
        job_type="snp",
        args=hpc_payload
    )
    
    logger.info(f"Mocked send_hpc_call called with job_uuid: {job_uuid}")

@pytest.mark.asyncio
async def test_mock_consume_response():
    """Simulate receiving a message from RabbitMQ via mocked consume."""
    logger.info("===== test_mock_consume_response =====")
    messenger = MockSOFIMessenger("amqp://guest:guest@rabbitmq/")

    async for response in messenger.consume():
        logger.info(f"Received mocked response: {response}")
        assert response["status"] == "success"
        assert "job_uuid" in response
        break
