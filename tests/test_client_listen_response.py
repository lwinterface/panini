from anthill.test_client import TestClient
from tests.global_object import Global

# no need to run anthill
client = TestClient()


global_object = Global()


@client.listen('foo')
def foo_listener(topic, message):
    return {'data': message['data'] + 5}


def test_client_response_listener():
    response = client.request('foo', {'data': 1})

    assert response['data'] == 6
