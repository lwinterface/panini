from panini.test_client import TestClient
from tests.helper import Global

# no need to run panini
client = TestClient()


global_object = Global()


@client.listen("test_client_listen.foo")
def foo_listener(subject, message):
    global_object.public_variable = message["data"] + 1


def test_client_listener():
    client.publish("test_client_listen.foo", {"data": 1})
    client.wait(count=1)

    assert global_object.public_variable == 2
