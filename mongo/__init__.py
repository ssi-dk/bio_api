from os import getenv
import sys

import sshtunnel

from .mongo_api import MongoAPI

MONGO_CONNECTION_STRING = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
MONGO_USE_TUNNEL = getenv('MONGO_USE_TUNNEL', False)
MONGO_TUNNEL_IP = getenv('MONGO_TUNNEL_IP', False)
MONGO_TUNNEL_USERNAME = getenv('MONGO_TUNNEL_USERNAME', False)
MONGO_TUNNEL_PASSWORD = getenv('MONGO_TUNNEL_PASSWORD', False)
MONGO_TUNNEL_REMOTE_BIND = getenv('MONGO_TUNNEL_REMOTE_BIND', False)
MONGO_TUNNEL_LOCAL_BIND = getenv('MONGO_TUNNEL_LOCAL_BIND', False)

print(f"Connection string: {MONGO_CONNECTION_STRING}")
print(f"Use SSH tunnel:  {MONGO_USE_TUNNEL}")
print(f"Tunnel IP:  {MONGO_TUNNEL_IP}")
print(f"Tunnel username:  {MONGO_TUNNEL_USERNAME}")
print(f"Remote bind IP:  {MONGO_TUNNEL_REMOTE_BIND}")
print(f"Local bind IP:  {MONGO_TUNNEL_LOCAL_BIND}")

if MONGO_USE_TUNNEL:
    sshtunnel.open_tunnel(
    (MONGO_TUNNEL_IP, 22),  # IP of dev2.sofi-platform.dk
    ssh_username=MONGO_TUNNEL_USERNAME,
    ssh_password=MONGO_TUNNEL_PASSWORD,
    remote_bind_address=(MONGO_TUNNEL_REMOTE_BIND, 27017),  # IP of dpfvst-002.computerome.local in DELPHI dev/test env
    local_bind_address=(MONGO_TUNNEL_LOCAL_BIND, 27017)
)

mongo_api = MongoAPI(MONGO_CONNECTION_STRING)