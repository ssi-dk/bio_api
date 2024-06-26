import requests

base_url = 'http://bio_api:8000'

def dictify_path(dotted_path:str, value:any):
    path_elements = dotted_path.split('.')
    emp_dict = p_list = {}
    i = 0
    for item in path_elements:
        i += 1
        if i == len(path_elements):
            p_list[item] = value
        else:
            p_list[item] = {}
        p_list = p_list[item]
    return emp_dict

def recursive_merge(dict1, dict2):
    for key, value in dict2.items():
        if key in dict1 and isinstance(dict1[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            dict1[key] = recursive_merge(dict1[key], value)
        else:
            # Merge non-dictionary values
            dict1[key] = value
    return dict1

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response

def call_nearest_neighbors(
        seq_collection: str,
        filtering: dict,
        input_mongo_id: str,
        profile_field_path: str,
        cutoff: int,
        unknowns_are_diffs: bool
    ):
    url = base_url + '/v1/nearest_neighbors'
    rest_response = requests.post(
        url,
        json={
            'seq_collection': seq_collection,
            'filtering': filtering,
            'input_mongo_id':  input_mongo_id,
            'profile_field_path': profile_field_path,
            'cutoff': cutoff,
            'unknowns_are_diffs': unknowns_are_diffs
            }
    )
    return rest_response

def call_nn_status(job_id: str):
    url = base_url + f'/v1/nearest_neighbors/{job_id}'
    rest_response = requests.get(url, params={'level': 'status'})
    return rest_response

def call_nn_result(job_id: str):
    url = base_url + f'/v1/nearest_neighbors/{job_id}'
    rest_response = requests.get(url)
    return rest_response

def call_dmx_from_mongodb(
    seq_collection:str,
    seqid_field_path: str,
    profile_field_path:str,
    mongo_ids:list | None):
    if not mongo_ids:
        print("mongo_ids not provided - use all samples in collection")
    url = base_url + '/v1/distance_calculations'
    rest_response = requests.post(
        url,
        json={
            'seq_collection': seq_collection,
            'seqid_field_path': seqid_field_path,
            'profile_field_path': profile_field_path,
            'seq_mongo_ids': mongo_ids
            }
    )
    return rest_response

def call_dmx_status(job_id:str):
    url = base_url + f'/v1/distance_calculations/{job_id}'
    rest_response = requests.get(url, params={'level': 'status'})
    return rest_response

def call_dmx_result(job_id: str):
    url = base_url + f'/v1/distance_calculations/{job_id}'
    rest_response = requests.get(url)
    return rest_response

def call_hc_tree_from_dmx_job(dmx_job: str, method:str):
    url = base_url + '/v1/trees'
    rest_response = requests.post(
        url,
        json={
            'dmx_job': dmx_job,
            'method': method
            }
    )
    return rest_response

def call_hc_tree_status(job_id):
    url = base_url + f'/v1/trees/{job_id}'
    rest_response = requests.get(url, params={'level': 'status'})
    return rest_response

def call_hc_tree_result(job_id):
    url = base_url + f'/v1/trees/{job_id}'
    rest_response = requests.get(url, params={'job_id': job_id})
    return rest_response
