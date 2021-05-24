import asyncio

import pytest

from panini.test_client import TestClient
from panini import app as panini_app

msg_num = 10


def run_panini():
    app = panini_app.App(
        service_name="test_non_blocking_request",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_non_blocking_request.start")
    async def non_blocking_requests(msg):
        def handle_response(msg):
            app.publish_sync(
                "test_non_blocking_request.finalize",
                {"success": True, "data_type": type(msg.data).__name__},
            )

        for _ in range(msg_num):
            await app.request(
                subject="test_non_blocking_request.foo",
                message={"data": 1},
                callback=handle_response,
            )

        return {"success": True}

    @app.listen("test_non_blocking_request.foo")
    async def subject_for_requests_listener(msg):
        await asyncio.sleep(0.5)
        return {"success": True, "data": "request has been processed"}

    app.start()


result = None


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini, socket_timeout=100)

    @client.listen("test_non_blocking_request.finalize")
    def helper(msg):
        global result
        result = msg.data

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_non_blocking_request(client):
    response = client.request("test_non_blocking_request.start", {})
    assert response["success"] is True

    client.wait(msg_num)
    assert isinstance(result, dict)
    assert result["success"] is True
    assert result["data_type"] == "bytes"
