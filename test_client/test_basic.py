import client_functions

def test_pytest():
    assert 1 == 1

def test_hello_world():
    result = client_functions.call_hello_world()
    assert result.json() == {'message': 'Hello World'}

def test_dmx_from_request():
    result = client_functions.call_dmx_from_request(
        loci=['locus1', 'locus2', 'locus3'],
        profiles={
            'id_1': {'locus1': 1, 'locus2': 3, 'locus3': '-'},
            'id_2': {'locus1': 0, 'locus2': '?', 'locus3':'3'},
            'id_3': {'locus1': 10, 'locus2': 41, 'locus3': 4}
        }
    )
    assert result.status_code == 200

def test_dmx_from_local_file():
    result = client_functions.call_dmx_from_local_file(
        file_path = 'test_input/BN_alleles_export.tsv'
    )
    assert result.status_code == 200