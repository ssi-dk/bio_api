from os import getenv

import sshtunnel
import pymongo

with sshtunnel.open_tunnel(
    ('10.32.244.37', 22),  # IP of dev2.sofi-platform.dk
    ssh_username="fingru",
    ssh_password=(input("SSH password: ")),
    remote_bind_address=('10.45.129.11', 27017),  # IP of dpfvst-002.computerome.local in DELPHI dev/test env
    local_bind_address=('0.0.0.0', 27017)
) as tunnel:
    print("Tunnel established.")
    mongo_string = getenv("BIO_API_MONGO_CONNECTION")
    print(mongo_string)
    connection = pymongo.MongoClient(mongo_string, directConnection=True)
    db = connection.get_database()
    sample = db.samples.find_one()
    print(sample)
    connection.close()

print('FINISH!')


# connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
# print(f"Connection string: {connection_string}")
# session = MongoSession(uri=connection_string, host='dpfvst-002.computerome.local')
# db = session.connection['sofi-dev']

# sample = db.samples.find_one()
# print(sample)