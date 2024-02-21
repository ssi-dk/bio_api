import pytest
from os import getenv
import pymongo

import client_functions
from profile2mongo import profile2mongo

connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
connection = pymongo.MongoClient(connection_string)
db = connection.get_database()
print(f"Connection string: {connection_string}")
mongo_ids = profile2mongo(db, 'input_data/BN_alleles_export_5.tsv', 'test_samples')

def test_dmx_from_mongodb():
    result = client_functions.call_dmx_from_mongodb(
    collection='samples',
    seqid_field_path='ID',
    profile_field_path='profile',
    mongo_ids=mongo_ids)
    assert result.status_code == 200

db['test_samples'].drop()