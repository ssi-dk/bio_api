import argparse
from datetime import datetime
from os import getenv
from json import dumps
from string import ascii_letters,digits 
from random import choice
from time import sleep

import pymongo
from bson.objectid import ObjectId

from microreact_integration import common, functions

import client_functions
 
lettersdigits=ascii_letters+digits 
 
def random_string(n): 
   my_list = [choice(lettersdigits) for _ in range(n)] 
   my_str = ''.join(my_list) 
   return my_str

help_desc = ("Create a test project in Microreact using all samples from a MongoDB collection. "
             "A data table with fake metadata will be generated automatically. "
             )
parser = argparse.ArgumentParser(description=help_desc)
parser.add_argument(
    "collection",
    help="Name of MongoDB collection that contains the samples to use."
    )
parser.add_argument(
    "--project_name",
    help="Project name (can be changed later in web interface)",
    default=common.USERNAME + '_' + str(datetime.now().isoformat(timespec='seconds'))
    )
group = parser.add_mutually_exclusive_group()
group.add_argument(
    "--file",
    help="Store the project as a file with this name instead of uploading it through the upload API",
    )
group.add_argument(
    "--noverify",
    help="Do not verify SSL certificate of Microreact host",
    action="store_true"
    )
args = parser.parse_args()

connection_string = getenv('BIO_API_MONGO_CONNECTION', 'mongodb://mongodb:27017/bio_api_test')
connection:pymongo.MongoClient = pymongo.MongoClient(connection_string)
db = connection.get_database('bio_api_test')
collection: str = args.collection
samples = db[collection].find()
sample_count = db[collection].count_documents({})
print(f"Found {sample_count} samples in {collection}")

# Initiate distance calculation
dmx_post_response = client_functions.call_dmx_from_mongodb(
    seq_collection=collection,
    seqid_field_path='categories.sample_info.summary.sofi_sequence_id',
    profile_field_path='categories.cgmlst.report.alleles',
)
assert dmx_post_response.status_code == 201
assert 'job_id' in dmx_post_response.json()
dmx_job_id = dmx_post_response.json()['job_id']
print(f"DMX job id: {dmx_job_id}")

# Check status of distance calculation
dmx_job_status = ''
while not dmx_job_status == 'completed':
    dmx_status_response = client_functions.call_dmx_status(dmx_job_id)
    print(dmx_status_response)
    assert dmx_status_response.status_code == 200
    dmx_job = dmx_status_response.json()
    assert 'status' in dmx_job
    dmx_job_status = dmx_job['status']
    print(f'DMX job status: {dmx_job_status}')
    sleep(1)

# Get the actual distance matrix
dmx_result_response = client_functions.call_dmx_result(dmx_job_id)
print(dmx_result_response)
assert dmx_result_response.status_code == 200
dmx_job = dmx_result_response.json()
distances = dmx_job['result']['distances']
print("Distance matrix:")
print(distances)

# Initiate tree calculation
tree_post_response = client_functions.call_hc_tree_from_dmx_job(dmx_job_id, 'single')
assert tree_post_response.status_code == 201
assert 'job_id' in tree_post_response.json()
tree_job_id = tree_post_response.json()['job_id']
print(f"Tree job id: {tree_job_id}")

# Check status of tree calculation
tree_job_status = ''
while not tree_job_status == 'completed':
    tree_get_response = client_functions.call_hc_tree_result(tree_job_id)
    print(tree_get_response)
    assert tree_get_response.status_code == 200
    tree_job = tree_get_response.json()
    assert 'status' in tree_job
    tree_job_status = tree_job['status']
    print(f'Tree job status: {tree_job_status}')
    sleep(1)

# Create minimal metadata set
seq_to_mongo:dict = dmx_job['result']['seq_to_mongo']
metadata_keys = ['seq_id', 'db_id']

metadata_values = list()
for k, v in seq_to_mongo.items():
    metadata_values.append([k, str(v)])

# Add fake metadata
metadata_keys.extend(['cpr', 'navn', 'mk', 'alder', 'landnavn', 'kmanavn'])
row: list
for row in metadata_values:
    for n in range(6):
        row.append(random_string(10))

if args.file:
    functions.new_project_file(
        project_name=args.project_name,
        tree_calcs=[tree_job],
        metadata_keys=metadata_keys,
        metadata_values=metadata_values,
        file_name = args.file
    )
else:
    print(f"Sending request to {common.MICROREACT_BASE_URL}")
    rest_response = functions.new_project(
        project_name=args.project_name,
        tree_calcs=[tree_job],
        metadata_keys=metadata_keys,
        metadata_values=metadata_values,
        raw_matrices=[distances],
        mr_access_token=common.MICROREACT_ACCESS_TOKEN,
        mr_base_url=common.MICROREACT_BASE_URL,
        verify = not args.noverify
        )
    print(f"HTTP response code: {str(rest_response)}")
    print("Response as actual JSON:")
    print(dumps(rest_response.json()))