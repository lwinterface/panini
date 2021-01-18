from anthill.testclient import TestClient
from tests.global_object import Global

# no need to run anthill
client = TestClient()


global_object = Global()


@client.listen('foo')
def foo_listener(topic, message):
    global_object.public_variable = message['data'] + 1


def test_client_listener():
    client.publish('foo', {'data': 1})
    client.wait(count=1)

    assert global_object.public_variable == 2
