from panini.test_client import TestClient
from tests.helper import Global

# no need to run panini
client = TestClient()


global_object = Global()


@client.listen("test_client_listen_response.foo")
def foo_listener(msg):
    return {"data": msg.data["data"] + 5}


client.start()


def test_client_response_listener():
    response = client.request("test_client_listen_response.foo", {"data": 1})

    assert response["data"] == 6
