import requests

base_url = 'http://bio_api:8001'

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response

def call_dmx_from_mongodb(
    collection:str,
    seqid_field_path: str,
    profile_field_path:str,
    mongo_ids:list):
    url = base_url + '/v1/distance_calculation/from_cgmlst'
    rest_response = requests.post(
        url,
        json={
            'collection': collection,
            'seqid_field_path': seqid_field_path,
            'profile_field_path': profile_field_path,
            'mongo_ids': mongo_ids
            }
    )
    return rest_response

def call_dmx_status(job_id: str):
    url = base_url + '/v1/distance_calculation/status/'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response

def call_hc_tree(distances: dict, method: str):
    url = base_url + '/v1/tree/hc'
    response = requests.post(
        url,
        json={
            'distances': distances,
            'method': method
        }
    )
    return response