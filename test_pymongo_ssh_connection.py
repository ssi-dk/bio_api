from os import getenv

from pymongo_ssh import MongoSession

connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
session = MongoSession(uri=connection_string, host='dpfvst-002.computerome.local')
db = session.connection['sofi-dev']

sample = db.samples.find_one()
print(sample)