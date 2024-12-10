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


def test_nearest_neighbors():
    # result = client_functions.call_nearest_neighbors(
    #     seq_collection='test_samples',
    #     filtering={},
    #     input_mongo_id=mongo_ids[0],
    #     profile_field_path='cgmlst.profile',
    #     cutoff=1000,
    #     unknowns_are_diffs=True
    # )
    # assert result.status_code == 201
    # assert 'job_id' in result.json()
    # job_id = result.json()['job_id']

    # result = client_functions.call_nn_result(job_id=job_id)
    # assert result.status_code == 200
    # j = result.json()
    # assert 'status' in j
    # assert j['status'] == 'completed'
    # assert 'result' in j
    # assert type(j['result']) is list

    # Initiate nn calculation
    response = client_functions.call_nearest_neighbors(
        seq_collection='test_samples',
        filtering={},
        input_mongo_id=mongo_ids[0],
        profile_field_path='cgmlst.profile',
        cutoff=30,
        unknowns_are_diffs=True
    )
    assert response.status_code == 201
    nn_post_resp = response.json()
    assert 'job_id' in nn_post_resp
    assert 'status' in nn_post_resp
    job_id = nn_post_resp['job_id']
    status = nn_post_resp['status']

    # sleep(5)
    # result = client_functions.call_nn_result(job_id=job_id)
    # assert result.status_code == 200
    # j = result.json()
    # assert 'status' in j
    # assert j['status'] == 'completed'
    # assert 'result' in j
    # assert type(j['result']) is list

    # Check status of nn calculation
    while status == 'init':
        response = client_functions.call_nn_status(job_id)
        assert response.status_code == 200
        nn_get_resp = response.json()
        assert 'job_id' in nn_get_resp
        assert 'status' in nn_get_resp
        status = nn_get_resp['status']
        sleep(1)

    assert status == 'completed'

    response = client_functions.call_nn_result(job_id)
    assert response.status_code == 200
    # nn_get_resp = response.json()
    # assert 'result' in nn_get_resp