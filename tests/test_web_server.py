import json

import pytest
from aiohttp import web
from panini import app as panini_app
from panini.test_client import TestClient


def run_panini():

    app = panini_app.App(
        service_name="test_web_server",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False
    )

    app.setup_web_server(port=8084)

    @app.listen("test_web_server.foo")
    async def foo(msg):
        msg.data["data"] += 1
        return msg.data

    @app.http.post("/test_web_server/bar")
    async def post_listener(request):
        data = await request.json()
        data["data"] += 2
        return web.json_response(data)

    app.start()


@pytest.fixture(scope="module")
def client():
    # provide parameter for using web_server - use_web_server; for waiting for web_server setup - sleep_time;
    client = TestClient(
        run_panini=run_panini,
        use_web_server=True,
        base_web_server_url="http://127.0.0.1:8084",
    )
    client.start()
    yield client
    client.stop()


def test_request_and_post(client):
    response = {"data": 0}
    for i in range(5):
        response = client.request(
            "test_web_server.foo", message={"data": response["data"]}
        )
        response = client.http_session.post(
            "test_web_server/bar", data=json.dumps({"data": response["data"]})
        )
        assert response.status_code == 200, response.text
        response = response.json()
        assert response["data"] == 3 * (i + 1)
