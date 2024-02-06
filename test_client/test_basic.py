from client_functions import hello_world

def test_pytest():
    assert 1 == 1

def test_hello_world():
    result = hello_world()
    assert result.json() == {'message': 'Hello World'}