import pytest

from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_request",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_request.start")
    async def publish_request(msg):
        response = await app.request(subject="test_request.foo", message={"data": 1})
        return response

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_request.foo")
    def foo_listener(msg):
        msg.data["data"] += 1
        return msg.data

    client.start()
    yield client
    client.stop()


def test_publish_request(client):
    response = client.request("test_request.start", {})
    assert response["data"] == 2
