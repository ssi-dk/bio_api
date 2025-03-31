# test_rabbitmq.py

import pytest
import asyncio
import uuid
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


@pytest.mark.asyncio
async def test_mock_rabbitmq_connect_success(mock_successful_rabbitmq_connection):
    """Mock successful RabbitMQ connection"""
    logger.info("===== test_mock_rabbitmq_connect_success =====")

    connection = await mock_successful_rabbitmq_connection("amqp://guest:guest@rabbitmq/")
    logger.info("Mocked RabbitMQ connection established.")
    assert connection is not None
    mock_successful_rabbitmq_connection.assert_called_once()


@pytest.mark.asyncio
async def test_mock_rabbitmq_connect_failure(mock_failed_rabbitmq_connection):
    """Simulate RabbitMQ connection failure (mocked)"""
    logger.info("===== test_mock_rabbitmq_connect_failure =====")

    mock_connect, mock_sleep = mock_failed_rabbitmq_connection
    tries = 3

    for i in range(tries):
        try:
            await mock_connect("amqp://guest:guest@rabbitmq/")
        except AMQPConnectionError:
            logger.info(f"Connection attempt {i+1} failed. Retrying...")
            await asyncio.sleep(1)

    assert mock_connect.call_count == tries
    assert mock_sleep.call_count == tries
    logger.info("All retries attempted and successfully failed.")


@pytest.mark.asyncio
async def test_mock_send_hpc_call(mock_messenger):
    """Simulate sending a message to RabbitMQ via mocked SOFIMessenger"""
    logger.info("===== test_mock_send_hpc_call =====")

    job_uuid = uuid.uuid4().hex
    hpc_payload = {
        "args": ["-h"],
        "cpus": 1,
        "memGB": 4,
        "group": "fvst_ssi",
        "nodes": "testnode"
    }

    await mock_messenger.send_hpc_call(uuid=job_uuid, job_type="snp", args=hpc_payload)

    mock_messenger.send_hpc_call.assert_called_once_with(
        uuid=job_uuid,
        job_type="snp",
        args=hpc_payload
    )
    
    logger.info(f"Mocked send_hpc_call called with job_uuid: {job_uuid}")

@pytest.mark.asyncio
async def test_send_hpc_call_failure(monkeypatch, mock_messenger):
    async def failing_send(*args, **kwargs):
        raise RuntimeError("Simulated failure")
    mock_messenger.send_hpc_call = AsyncMock(side_effect=failing_send)

    with pytest.raises(RuntimeError):
        await mock_messenger.send_hpc_call(uuid="fake", job_type="snp", args={})

@pytest.mark.asyncio
async def test_mock_consume_response(mock_messenger):
    """Simulate receiving a message from RabbitMQ via mocked consume"""
    logger.info("===== test_mock_consume_response =====")

    async for response in mock_messenger.consume():
        logger.info(f"Received mocked response: {response}")
        assert response["status"] == "success"
        assert "job_uuid" in response
        break

