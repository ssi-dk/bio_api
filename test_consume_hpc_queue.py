import asyncio
import sys
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument(
    "--queue_name",
    default='hpc_response',
    help="RabbitMQ queue to consume. Here you can enter 'hpc_call' to monitor calls. Default is 'hpc_response' which will monitor responses."
)
args = parser.parse_args()

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from sofi_messenger.src import sofi_messenger


async def main() -> None:
    host = "amqp://guest:guest@rabbitmq/"
    listener = sofi_messenger.SOFIMessenger(host)

    hpc_response_iter = listener.consume(args.queue_name)
    async for hpc_response in hpc_response_iter:
        print(f"Received HPC response: {hpc_response}")


if __name__ == "__main__":
    asyncio.run(main())