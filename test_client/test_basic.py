from client_functions import call_hello_world, call_dmx_from_profiles

def test_pytest():
    assert 1 == 1

def test_hello_world():
    result = call_hello_world()
    assert result.json() == {'message': 'Hello World'}

def test_dmx_from_profiles():
    result = call_dmx_from_profiles(
        loci=['locus1', 'locus2', 'locus3'],
        profiles={
            'id_1': {'locus1': 1, 'locus2': 3, 'locus3': '-'},
            'id_2': {'locus1': 0, 'locus2': '?', 'locus3':'3'},
            'id_3': {'locus1': 10, 'locus2': 41, 'locus3': 4}
        }
    )
    assert result.status_code == 200