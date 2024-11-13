import asyncio
import sys
import os
from os import getenv

import pymongo
import sshtunnel

from mongo import MongoAPI
from calculations import SNPCalculation, HPCResources, MissingDataException

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

        hpc_r: HPCResources = HPCResources(cpus=2, memGB=8, nodes='1, 2')
        snp_calc = SNPCalculation(
            mongo_api=mongo_api,
            seq_collection='samples',
            seqid_field_path='categories.sample_info.summary.sofi_sequence_id',
            filename_field_path='categories.contigs.summary.data',
            seq_mongo_ids=['666febab9871ba945a1a11f0', '666febac9871ba945a1a11f1', '666febad9871ba945a1a11f2'],
            reference_mongo_id='666febad9871ba945a1a11f3',
            depth='7',
            ignore_hz=False,
        )
        print("Object created.")

        # TODO uncomment when we have actual fasta files that are actually referred in the sample docs
        # profile_count, cursor = await snp_calc.query_mongodb_for_filenames()

        with sshtunnel.open_tunnel(
            (MONGO_TUNNEL_IP, 22),  # IP of dev2.sofi-platform.dk
            ssh_username=MONGO_TUNNEL_USERNAME,
            ssh_password=MONGO_TUNNEL_PASSWORD,
            remote_bind_address=(MONGO_TUNNEL_REMOTE_BIND, 27017),  # IP of dpfvst-002.computerome.local in DELPHI dev/test env
            local_bind_address=(MONGO_TUNNEL_LOCAL_BIND, 27017)
        ) as tunnel:
            print("Tunnel established:")
            print(tunnel)
            snp_calc._id = await snp_calc.insert_document()
        print("SNP object saved.")

        # Åbn RabbitMQ tunnel
        #   await snp_calc.calculate()
        # Luk RabbitMQ tunnel


if __name__ == "__main__":
    asyncio.run(main())