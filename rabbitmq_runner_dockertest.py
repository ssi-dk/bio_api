import asyncio
import uuid
import os
import time
import sys
print("Current PYTHONPATH:", sys.path)
print("Files in /app:", os.listdir("/app"))
from sofi_messenger import SOFIMessenger
from aio_pika.exceptions import AMQPConnectionError
from aio_pika import connect_robust

"""
Test to see if we from local container can connect to the rabbitmq using functionalities from the sofi_messenger github
"""

#if AMQP_HOST is from the local run using ssh tunnel, discuss with KRKI the HOST 
AMQP_HOST = os.getenv("AMQP_HOST", "amqp://guest:guest@rabbitmq/") # "amqp://guest:guest@localhost/"
messenger = SOFIMessenger(AMQP_HOST)

async def wait_for_rabbitmq():
    retries = 10
    for i in range(retries):
        try:
            connection = await connect_robust(AMQP_HOST)
            async with connection:
                print("---------------------------------------------------\n\n\nConnected to RabbitMQ!\n\n\n---------------------------------------------------")
                return
        except AMQPConnectionError:
            print(f"Retry no. {i+1} to connect to RabbitMQ")
            await asyncio.sleep(10)
    print("---------------------------------------------------\n\n\nFailed to connect to RabbitMQ!\n\n\n---------------------------------------------------")
    exit(1)

#similar to the connection of SOFIMessenger from RSK -> https://github.com/ssi-dk/sofi_messenger/blob/main/src/sofi_messenger/sofi_messenger.py#L151C2-L181C24

async def send_test_hpc_call():
    try:
        job_uuid = uuid.uuid4().hex
        hpc_resources = {
            "args": ["-h"],
            "cpus": 1,  
            "memGB": 4,  
            "group": "fvst_ssi",
            "nodes": "rabbitmq test"
        }
        await messenger.send_hpc_call(uuid=job_uuid, job_type="snp", **hpc_resources)
        print(f"Sent HPC job request with UUID: {job_uuid}")
    except Exception as e:
        print(f"Error sending HPC job: {e}")

async def main():
    await wait_for_rabbitmq()
    await send_test_hpc_call()

if __name__ == "__main__":
    asyncio.run(main())
