import pytest

from panini.test_client import TestClient
from panini import app as panini_app

RESPONSE = {"on_start_task_finished": False}

def run_panini():
    app = panini_app.App(
        service_name="test_request",
        host="127.0.0.1",
        port=4222,
    )

    @app.on_start_task()
    async def on_start():
        global RESPONSE
        RESPONSE["on_start_task_finished"] = True

    @app.listen("test_request.start")
    async def publish_request(msg):
        return RESPONSE

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    client.start()
    yield client
    client.stop()


def test_on_start(client):
    response = client.request("test_request.start", {})
    assert response["on_start_task_finished"]
