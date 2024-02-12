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

def call_dmx_from_local_file(file_name: str):
    url = base_url + '/v1/distance_matrix/from_local_file'
    rest_response = requests.post(
        url,
        json={
            'file_name': file_name
            }
    )
    return rest_response

def call_dmx_from_mongodb(collection:str, mongo_ids:list, field_path:str):
    url = base_url + '/v1/distance_matrix/from_mongodb'
    rest_response = requests.post(
        url,
        json={
            'collection': collection,
            'field_path': field_path,
            'mongo_ids': ['6565e8ee4a2ab7276967b8a0']
            }
    )
    return rest_response
