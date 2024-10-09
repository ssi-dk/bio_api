import asyncio
import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
from sofi_messenger.src import sofi_messenger


async def main() -> None:
    host = "amqp://guest:guest@rabbitmq/"
    listener = sofi_messenger.SOFIMessenger(host)

    hpc_response_iter = listener.consume()
    async for hpc_response in hpc_response_iter:
        print(f"Received HPC response: {hpc_response}")


if __name__ == "__main__":
    asyncio.run(main())