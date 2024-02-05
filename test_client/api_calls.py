import requests

base_url = 'bio_api:7000'

def hello_world():
    url = base_url + '/'
    rest_response = requests.get(url)
    return rest_response
