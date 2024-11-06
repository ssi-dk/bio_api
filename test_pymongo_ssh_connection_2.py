from os import getenv

from pymongo import MongoClient
from sshtunnel import SSHTunnelForwarder

ssh_host = 'sshhost'
ssh_port = 22
ssh_user = 'sshuser'
ssh_private_key_path = 'privatekey'
mongo_host = 'mongodbserver'
mongo_port = 27017
mongo_user = 'user'
mongo_password = 'password'
mongo_db = 'db'
collection_name = 'collection_name'


try:
   with open(ssh_private_key_path, 'r') as f:
       print("Private key file is accessible.")
except FileNotFoundError:
   raise FileNotFoundError(f"Private key file not found at {ssh_private_key_path}")
except PermissionError:
   raise PermissionError(f"Permission denied for private key file at {ssh_private_key_path}")


with SSHTunnelForwarder(
   (ssh_host, ssh_port),
   ssh_username=ssh_user,
   ssh_pkey=ssh_private_key_path,
   remote_bind_address=(mongo_host, mongo_port)
) as tunnel:
    client = MongoClient(f'mongodb://{mongo_user}:{mongo_password}@127.0.0.1:{tunnel.local_bind_port}/{mongo_db}?compressors=disabled&gssapiServiceName=mongodb')


    db = client[mongo_db]
    collection = db[collection_name]
    document = collection.find_one()
    client.close()


# connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
# print(f"Connection string: {connection_string}")
# session = MongoSession(uri=connection_string, host='dpfvst-002.computerome.local')
# db = session.connection['sofi-dev']

# sample = db.samples.find_one()
# print(sample)