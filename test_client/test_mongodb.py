import pytest

import client_functions
from profile2mongo import profile2mongo

@pytest.fixture
def mongo_ids():
    return profile2mongo('input_data/BN_alleles_export_5')

def xxx_dmx_from_request():
    result = client_functions.call_dmx_from_mongodb(
    collection='samples',
    seqid_field_path='ID',
    profile_field_path='profile',
    mongo_ids=mongo_ids)
    assert result.status_code == 200
