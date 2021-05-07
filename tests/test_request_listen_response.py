import pytest
from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_request_listen_response", host="127.0.0.1", port=4222
    )

    @app.listen("test_request_listen_response.start")
    async def start(msg):
        await app.request("test_request_listen_response.app.started", {"success": True})
        return {"success": True}

    app.start()


is_app_started = False


@pytest.fixture()
def client():
    client = TestClient(run_panini)

    @client.listen("test_request_listen_response.app.started")
    def app_started(msg):
        global is_app_started
        is_app_started = True
        return {"started": True}

    client.start()
    yield client
    client.stop()


def test_get_token(client):
    assert is_app_started is False
    response = client.request("test_request_listen_response.start", {})
    assert response["success"]
    assert is_app_started is True
