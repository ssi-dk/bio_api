from os import getenv

import sshtunnel
import pymongo
import asyncio

import test_init_snp_calculation

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
MONGO_USE_TUNNEL = getenv('MONGO_USE_TUNNEL', False)
MONGO_TUNNEL_IP = getenv('MONGO_TUNNEL_IP', False)
MONGO_TUNNEL_USERNAME = getenv('MONGO_TUNNEL_USERNAME', False)
MONGO_TUNNEL_PASSWORD = getenv('MONGO_TUNNEL_PASSWORD', False)
MONGO_TUNNEL_REMOTE_BIND = getenv('MONGO_TUNNEL_REMOTE_BIND', False)
MONGO_TUNNEL_LOCAL_BIND = getenv('MONGO_TUNNEL_LOCAL_BIND', False)

with sshtunnel.open_tunnel(
    (MONGO_TUNNEL_IP, 22),  # IP of dev2.sofi-platform.dk
    ssh_username=MONGO_TUNNEL_USERNAME,
    ssh_password=MONGO_TUNNEL_PASSWORD,
    remote_bind_address=(MONGO_TUNNEL_REMOTE_BIND, 27017),  # IP of dpfvst-002.computerome.local in DELPHI dev/test env
    local_bind_address=(MONGO_TUNNEL_LOCAL_BIND, 27017)
) as tunnel:
    print("Tunnel established:")
    print(tunnel)
    print("Testing MongoClient connection...")
    connection = pymongo.MongoClient(MONGO_CONNECTION_STRING, directConnection=True)
    db = connection.get_database()
    print("Collections:")
    print(db.list_collection_names())
    connection.close()
    print("Starting main script...")
    asyncio.run(test_init_snp_calculation.main())