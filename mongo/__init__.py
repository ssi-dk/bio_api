from os import getenv
import sys

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

mongo_api = MongoAPI(MONGO_CONNECTION_STRING)

sys.exit()