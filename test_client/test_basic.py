from client_functions import call_hello_world

def test_pytest():
    assert 1 == 1

def test_hello_world():
    result = call_hello_world()
    assert result.json() == {'message': 'Hello World'}