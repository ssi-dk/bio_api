import requests

base_url = 'http://bio_api:8000'

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response

def call_dmx_from_mongodb(
    seq_collection:str,
    seqid_field_path: str,
    profile_field_path:str,
    mongo_ids:list):
    url = base_url + '/v1/distance_calculation/from_cgmlst'
    rest_response = requests.post(
        url,
        json={
            'seq_collection': seq_collection,
            'seqid_field_path': seqid_field_path,
            'profile_field_path': profile_field_path,
            'mongo_ids': mongo_ids
            }
    )
    return rest_response

def call_dmx_status(job_id:str):
    url = base_url + '/v1/distance_calculation/status/'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response

def call_dmx_result(job_id: str):
    url = base_url + '/v1/distance_calculation/result/'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response

def call_hc_tree_from_rq(distances: dict, method: str):
    url = base_url + '/v1/hc_tree/from_request/'
    response = requests.post(
        url,
        json={
            'distances': distances,
            'method': method
        }
    )
    return response

def call_hc_tree_from_dmx_job(dmx_job: str, method:str):
    url = base_url + '/v1/hc_tree/from_dmx_job/'
    rest_response = requests.get(url, params={'dmx_job': dmx_job, 'method': method})
    return rest_response

def call_hc_tree_status(job_id):
    url = base_url + '/v1/hc_tree/status/'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response

def call_hc_tree_result(job_id):
    url = base_url + '/v1/hc_tree/result/'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response

def call_nearest_neighbors(
        seq_collection: str,
        input_mongo_id: str,
        profile_field_path: str,
        cutoff: int,
        unknowns_are_diffs: bool
    ):
    url = base_url + '/v1/nearest_neighbors/'
    rest_response = requests.post(
        url,
        json={
            'seq_collection': seq_collection,
            'input_mongo_id':  input_mongo_id,
            'profile_field_path': profile_field_path,
            'cutoff': cutoff,
            'unknowns_are_diffs': unknowns_are_diffs
            }
    )
    return rest_response