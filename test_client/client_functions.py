import requests

base_url = 'http://bio_api:8001'

def call_hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response
