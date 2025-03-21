import asyncio
import uuid
import os
import time
import sys
from sofi_messenger import SOFIMessenger
from aio_pika.exceptions import AMQPConnectionError
from aio_pika import connect_robust
import logging

"""
Test to see if we from local container can connect to the rabbitmq using functionalities from the sofi_messenger github
"""

# Set up logging to both console and a file
LOG_FILE = "rabbitmq_test.log"
logging.basicConfig(
    level=logging.INFO,  # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),  # Log to file
        logging.StreamHandler()  # Log to console
    ]
)
logger = logging.getLogger(__name__)

logger.info(f"testing docker information")
logger.info(f"Current PYTHONPATH:{sys.path}")
logger.info(f"Files in /app: {os.listdir("/app")}")

#if AMQP_HOST is from the local run using ssh tunnel, discuss with KRKI the HOST 
AMQP_HOST = os.getenv("AMQP_HOST", "amqp://guest:guest@rabbitmq/") # "amqp://guest:guest@localhost/"
messenger = SOFIMessenger(AMQP_HOST)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wait_for_rabbitmq():
    retries = 10
    time_delay = 10
    for i in range(retries):
        try:
            connection = await connect_robust(AMQP_HOST) # establish connection
            async with connection:
                logger.info(f"Connection try no {i+1} with logger host {AMQP_HOST}")
                logger.info("Succecfully connected to RabbitMQ!")
                #print("---------------------------------------------------\n\n\nConnected to RabbitMQ!\n\n\n---------------------------------------------------")
                return
        except AMQPConnectionError:
            #print(f"Retry no. {i+1} to connect to RabbitMQ")
            logger.info(f"Retry no. {i+1} to connect to RabbitMQ")
            await asyncio.sleep(time_delay)
    #print("---------------------------------------------------\n\n\nFailed to connect to RabbitMQ!\n\n\n---------------------------------------------------")
    exit(1)

#similar to the connection of SOFIMessenger from RSK -> https://github.com/ssi-dk/sofi_messenger/blob/main/src/sofi_messenger/sofi_messenger.py#L151C2-L181C24

async def send_test_hpc_call():
    logger.info(f"send_test_hpc_call() sending hpc call")
    try:
        job_uuid = uuid.uuid4().hex
        hpc_resources = {
            "args": ["-h"],
            "cpus": 1,  
            "memGB": 4,  
            "group": "fvst_ssi",
            "nodes": "????"
        }
        await messenger.send_hpc_call(uuid=job_uuid, job_type="snp", args=hpc_resources)

        logger.info(f"Sent HPC job request with UUID: {job_uuid}")
    except Exception as e:
        logger.info(f"Error sending HPC job: {e}")

async def consume_test_response():
    logger.info(f"consume_test_response() waiting for HPC response: {response}")
    async for response in messenger.consume():
        logger.info(f"\n Received HPC response: {response}\n")
        break  # Stop after receiving one response

async def main():
    await wait_for_rabbitmq()
    #await send_test_hpc_call()
    job_uuid = await send_test_hpc_call()  # Send a test job
    if job_uuid:
        await consume_test_response()  # Listen for a response

if __name__ == "__main__":
    asyncio.run(main())
