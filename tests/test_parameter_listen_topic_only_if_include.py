import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path


def run_panini():
    app = panini_app.App(
        service_name="test_listen_topic_only_if_include",
        host="127.0.0.1",
        port=4222,
        listen_topic_only_if_include=["foo", "bar"],
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("start")
    async def start(topic, message):
        return {"data": 1}

    @app.listen("foo")
    async def foo(topic, message):
        return {"data": 2}

    @app.listen("bar")
    async def start(topic, message):
        return {"data": 3}

    app.start()


client = TestClient(run_panini)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_listen_topic_only_if_include():
    response = client.request("foo", {})
    assert response["data"] == 2

    response = client.request("bar", {})
    assert response["data"] == 3

    with pytest.raises(OSError):
        client.request("start", {})
