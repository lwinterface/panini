from anthill.testclient import TestClient
from tests.global_object import Global


client = TestClient()


global_object = Global()


@client.listen('foo')
def foo_handler(topic, message):
    return {'data': message['data'] + 5}


def test_client_response_handler():
    response = client.request('foo', {'data': 1})

    assert response['data'] == 6
