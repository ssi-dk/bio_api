import requests

base_url = 'http://bio_api:8001'

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response

def call_dmx_from_profiles(loci:list, profiles:dict):
    url = base_url + '/v1/distance_matrix/from_profiles'
    rest_response = requests.post(
        url,
        json={
            'loci': loci,
            'profiles': profiles
            }
    )
    return rest_response
