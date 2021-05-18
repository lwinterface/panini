import asyncio
import time

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
        await asyncio.sleep(1.1)
        return msg.data

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini, socket_timeout=3, listener_socket_timeout=1)
    client.start()
    yield client
    client.stop()


def test_publish_request(client):
    time.sleep(1.5)
    for _ in range(3):
        response = client.request("test_request.start", {"success": True})
        assert response["success"] is True
