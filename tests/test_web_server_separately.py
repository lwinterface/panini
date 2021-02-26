import time
import json

import pytest
from aiohttp import web
from panini import app as panini_app
from panini.test_client import HTTPSessionTestClient
from panini.utils.helper import start_process
from .helper import get_testing_logs_directory_path


def run_panini():

    app = panini_app.App(
        service_name="test_web_server_separately",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        web_server=True,
        web_port=8084,
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.http.get("/get")
    async def get_listener(request):
        return web.Response(text="get response")

    @app.http.post("/post")
    async def post_listener(request):
        data = await request.json()
        data["data"] += 1
        return web.json_response(data)

    @app.http.view("/rest/endpoint")
    class RESTView(web.View):
        async def get(self):
            return await get_listener(self.request)

        async def post(self):
            return await post_listener(self.request)

    app.start()


# if we use raw HTTPSessionTestClient - we need to run panini manually and wait for setup
@pytest.fixture(scope="session", autouse=True)
def start_client():
    start_process(run_panini)
    time.sleep(2)


client = HTTPSessionTestClient(
    base_url="http://127.0.0.1:8084"
)  # handles only http requests


@pytest.mark.parametrize("url", ["get", "rest/endpoint"])
def test_get(url):
    response = client.get(url)
    assert response.status_code == 200
    assert response.text == "get response"


def test_get_invalid():
    response = client.get("get/invalid")
    assert response.status_code == 404, response.text


@pytest.mark.parametrize("url", ["post", "rest/endpoint"])
def test_post(url):
    response = client.post(url, data=json.dumps({"data": 1}))
    assert response.status_code == 200
    assert response.json()["data"] == 2


def test_post_invalid():
    response = client.post("post", data=json.dumps({"data": None}))
    assert response.status_code == 500, response.text
