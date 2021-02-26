import json

import pytest
from aiohttp import web
from panini import app as panini_app
from panini.test_client import TestClient
from .helper import get_testing_logs_directory_path


def run_panini():

    app = panini_app.App(
        service_name="test_web_server",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        web_server=True,
        web_port=8084,
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def foo(subject, message):
        message["data"] += 1
        return message

    @app.http.post("/bar")
    async def post_listener(request):
        data = await request.json()
        data["data"] += 2
        return web.json_response(data)

    app.start()


# provide parameter for using web_server - use_web_server; for waiting for web_server setup - sleep_time;
client = TestClient(
    run_panini=run_panini,
    use_web_server=True,
    base_web_server_url="http://127.0.0.1:8084",
)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start(sleep_time=3)


def test_request_and_post():
    response = {"data": 0}
    for i in range(5):
        response = client.request("foo", message={"data": response["data"]})
        response = client.http_session.post(
            "bar", data=json.dumps({"data": response["data"]})
        )
        assert response.status_code == 200, response.text
        response = response.json()
        assert response["data"] == 3 * (i + 1)
