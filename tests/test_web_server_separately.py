import time
import json

import pytest
from aiohttp import web
from anthill import app as ant_app
from anthill.test_client import HTTPSessionTestClient
from anthill.utils.helper import start_process
from .helper import get_testing_logs_directory_path


def run_anthill():

    app = ant_app.App(
        service_name="test_web_server_separately",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        web_server=True,
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


# if we use raw HTTPSessionTestClient - we need to run anthill manually and wait for setup
start_process(run_anthill)
time.sleep(1)

client = HTTPSessionTestClient()  # handles only http requests


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
