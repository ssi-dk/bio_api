import asyncio
import sys
import os
from os import getenv

import pymongo
import sshtunnel

from mongo import MongoAPI
from calculations import DebugCalculation, HPCResources, MissingDataException

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
MONGO_USE_TUNNEL = getenv('MONGO_USE_TUNNEL', False)
MONGO_TUNNEL_IP = getenv('MONGO_TUNNEL_IP', False)
MONGO_TUNNEL_USERNAME = getenv('MONGO_TUNNEL_USERNAME', False)
MONGO_TUNNEL_PASSWORD = getenv('MONGO_TUNNEL_PASSWORD', False)
MONGO_TUNNEL_REMOTE_BIND = getenv('MONGO_TUNNEL_REMOTE_BIND', False)
MONGO_TUNNEL_LOCAL_BIND = getenv('MONGO_TUNNEL_LOCAL_BIND', False)
RABBITMQ_PORT = 5672

async def main() -> None:
        mongo_api = MongoAPI(MONGO_CONNECTION_STRING)

        hpc_r: HPCResources = HPCResources(cpus=1, memGB=1, walltime=10)
        debug_calc = DebugCalculation(
            mongo_api=mongo_api,
            hpc_resources=hpc_r
        )
        print("Debug object created.")

        with sshtunnel.open_tunnel(
            (MONGO_TUNNEL_IP, 22),  # IP of dev2.sofi-platform.dk
            ssh_username=MONGO_TUNNEL_USERNAME,
            ssh_password=MONGO_TUNNEL_PASSWORD,
            remote_bind_address=(MONGO_TUNNEL_REMOTE_BIND, 27017),  # IP of dpfvst-002.computerome.local in DELPHI dev/test env
            local_bind_address=(MONGO_TUNNEL_LOCAL_BIND, 27017)
        ) as tunnel:
            print("Tunnel established:")
            print(tunnel)
            debug_calc._id = await debug_calc.insert_document()
            print(f"Debug object saved to MongoDB with _id {str(debug_calc._id)}")

        server = sshtunnel.SSHTunnelForwarder(
            'dev2.sofi-platform.dk',
            ssh_username=MONGO_TUNNEL_USERNAME,
            ssh_password=MONGO_TUNNEL_PASSWORD,
            remote_bind_address=('127.0.0.1', RABBITMQ_PORT),
            local_bind_address=('0.0.0.0', RABBITMQ_PORT)
        )
        server.start()
        await debug_calc.calculate()
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())