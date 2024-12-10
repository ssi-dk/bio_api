from os import getenv
import pymongo

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


def test_nearest_neighbors():
    result = client_functions.call_nearest_neighbors(
        seq_collection='test_samples',
        filtering={},
        input_mongo_id=mongo_ids[0],
        profile_field_path='cgmlst.profile',
        cutoff=1000,
        unknowns_are_diffs=True
    )
    assert result.status_code == 201
    assert 'job_id' in result.json()
    job_id = result.json()['job_id']

    # result = client_functions.call_nn_status(job_id=job_id)
    # assert result.status_code == 200
    # j = result.json()
    # assert 'status' in j
    # assert j['status'] == 'completed'
    # assert 'result' in j
    # assert type(j['result']) is list

    result = client_functions.call_nn_result(job_id=job_id)
    assert result.status_code == 200
    j = result.json()
    assert 'status' in j
    assert j['status'] == 'completed'
    assert 'result' in j
    assert type(j['result']) is list
