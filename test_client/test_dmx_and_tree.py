from os import getenv
import pymongo
from time import sleep

import client_functions
from profile2mongo import profile2mongo

connection_string = getenv('BIO_API MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
connection = pymongo.MongoClient(connection_string)
db = connection.get_database()
print(f"Connection string: {connection_string}")
mongo_ids = profile2mongo(
    db,
    'input_data/BN_alleles_export_50.tsv',
    collection='test_samples',
    seqid_field_path='sequence.id',
    profile_field_path='cgmlst.profile'
    )

def test_dmx_and_tree_from_mongodb():
    # Initiate distance calculation
    result = client_functions.call_dmx_from_mongodb(
        seq_collection='test_samples',
        seqid_field_path='sequence.id',
        profile_field_path='cgmlst.profile',
        mongo_ids=mongo_ids
    )
    assert result.status_code == 201
    r = result.json()
    assert 'job_id' in r
    assert 'status' in r
    job_id = result.json()['job_id']
    sleep(1)

    # Check status of distance calculation
    result = client_functions.call_dmx_status(job_id)
    assert result.status_code == 200
    j = result.json()
    assert 'status' in j
    assert j['status'] == 'completed'
    assert 'job_id' in j
    dmx_job = j['job_id']

    # Initiate tree calculation
    result = client_functions.call_hc_tree_from_dmx_job(dmx_job, 'single')
    assert result.status_code == 201
    j = result.json()
    assert 'status' in j
    tree_job = j['job_id']
    sleep(1)

    # Check status of tree calculation
    result = client_functions.call_hc_tree_status(tree_job)
    assert result.status_code == 200
    j = result.json()
    assert 'status' in j
    assert j['status'] == 'completed'

# db['test_samples'].drop()