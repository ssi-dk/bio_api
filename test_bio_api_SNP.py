#!/usr/bin/env python3

import requests
from pprint import pprint

host='http://localhost:8000'
path='/v1/nearest_neighbors'

payload = {
    'seq_collection': 'samples',
    'filtering': {},
    'profile_field_path': 'categories.cgmlst.report.alleles',
    'input_mongo_id': '67d13659b8afd75cc147bead',
    'cutoff': 15,
    'unknowns_are_diffs': False}

r = requests.post(f"{host}{path}",json=payload)
print(r.status_code)
print(r.json())

path='/v1/snp_calculations'

payload = {
    'seq_collection': 'samples',
    'seqid_field_path': '_id',
    'seq_mongo_ids': ['67ce9a1c17209b919fae4916'],
    'reference_mongo_id': '67d13659b8afd75cc147bead',
    'depth': 15,
    'ignore_hz': False}

r = requests.post(f"{host}{path}",json=payload)
print(r.status_code)
print(r.json())
