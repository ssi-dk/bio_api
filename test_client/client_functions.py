import requests

base_url = 'http://bio_api:8001'

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response

def call_dmx_from_request(loci:list, profiles:dict):
    url = base_url + '/v1/distance_matrix/from_request'
    rest_response = requests.post(
        url,
        json={
            'loci': loci,
            'profiles': profiles
            }
    )
    return rest_response

def call_dmx_from_local_file(file_path: str):
    url = base_url + '/v1/distance_matrix/from_local_file'
    rest_response = requests.post(
        url,
        json={
            'file_path': file_path
            }
    )
    return rest_response

def call_dmx_from_mongodb(
    collection:str,
    seqid_field_path: str,
    profile_field_path:str,
    mongo_ids:list):
    url = base_url + '/v1/distance_matrix/from_mongodb'
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

def call_dmx_from_mongodb_plus_tree(
    collection:str,
    seqid_field_path: str,
    profile_field_path:str,
    mongo_ids:list):
    url = base_url + '/v1/distance_matrix/from_mongodb'
    dmx_response = requests.post(
        url,
        json={
            'collection': collection,
            'seqid_field_path': seqid_field_path,
            'profile_field_path': profile_field_path,
            'mongo_ids': mongo_ids
            }
    )
    if dmx_response.status_code == 200:
        distances = dmx_response.json()['distance_matrix']
        # Get the tree
        url = base_url + '/v1/tree/hc'
        tree_response = requests.post(
        url,
        json={
            'distances': distances,
            'method': 'single',
            }
        )
        return tree_response
    else:
        print(f"dmx endpoint returned {dmx_response.status_code}")