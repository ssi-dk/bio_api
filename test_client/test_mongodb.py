import pytest

import client_functions
from profile2mongo import profile2mongo

mongo_ids = profile2mongo('input_data/BN_alleles_export_5.tsv')

def test_dmx_from_mongodb():
    result = client_functions.call_dmx_from_mongodb(
    collection='samples',
    seqid_field_path='ID',
    profile_field_path='profile',
    mongo_ids=mongo_ids)
    assert result.status_code == 200
