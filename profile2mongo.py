from os import getenv
from pandas import read_csv

import mongo

connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
print(f"Connection string: {connection_string}")
#mongo_api = mongo.MongoAPI(connection_string)

df = read_csv('test_input/example.tsv', sep='\t')