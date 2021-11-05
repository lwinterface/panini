import time
import json

import pytest
from aiohttp import web
from panini import app as panini_app
from panini.test_client import TestClient


def run_panini():

    app = panini_app.App(
        service_name="test_web_server_separately",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False
    )

    app.setup_web_server(port=8083)

    @app.http.get("/test_web_server_separately/get")
    async def get_listener(request):
        return web.Response(text="get response")

    @app.http.post("/test_web_server_separately/post")
    async def post_listener(request):
        data = await request.json()
        data["data"] += 1
        return web.json_response(data)

    @app.http.view("/test_web_server_separately/rest/endpoint")
    class RESTView(web.View):
        async def get(self):
            return await get_listener(self.request)

        async def post(self):
            return await post_listener(self.request)

    app.start()


# if we use raw HTTPSessionTestClient - we need to run panini manually and wait for setup
@pytest.fixture(scope="module")
def client():
    client = TestClient(
        run_panini, use_web_server=True, base_web_server_url="http://127.0.0.1:8083"
    )
    client.start()
    time.sleep(1)
    yield client
    client.stop()


@pytest.mark.parametrize(
    "url",
    ["test_web_server_separately/get", "test_web_server_separately/rest/endpoint"],
)
def test_get(url, client):
    response = client.http_session.get(url)
    assert response.status_code == 200
    assert response.text == "get response"


def test_get_invalid(client):
    response = client.http_session.get("test_web_server_separately/get/invalid")
    assert response.status_code == 404, response.text


@pytest.mark.parametrize(
    "url",
    ["test_web_server_separately/post", "test_web_server_separately/rest/endpoint"],
)
def test_post(url, client):
    response = client.http_session.post(url, data=json.dumps({"data": 1}))
    assert response.status_code == 200
    assert response.json()["data"] == 2


def test_post_invalid(client):
    response = client.http_session.post(
        "test_web_server_separately/post", data=json.dumps({"data": None})
    )
    assert response.status_code == 500, response.text
