from time import sleep

from api_calls import hello_world

sleep(1)  # Make sure uvicorn is ready

def test_pytest():
    assert 1 == 1

def test_hello_world():
    result = hello_world()
    assert result.json() == {'message': 'Hello World'}