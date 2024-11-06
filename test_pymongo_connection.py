from os import getenv

import pymongo

connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(connection_string)
connection = pymongo.MongoClient(connection_string)
db = connection.get_database()
sample = db.samples.find_one()
print(sample)