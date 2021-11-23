import pytest

from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_listen_subject_only_if_include",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )
    app.add_filters(include=["foo", "bar"])

    @app.listen("test_parameter_listen_subject_only_if_include.start")
    async def start(msg):
        return {"data": 1}

    @app.listen("test_parameter_listen_subject_only_if_include.foo")
    async def foo(msg):
        return {"data": 2}

    @app.listen("test_parameter_listen_subject_only_if_include.bar")
    async def start(msg):
        return {"data": 3}

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)
    client.start()
    yield client
    client.stop()


def test_listen_subject_only_if_include(client):
    response = client.request("test_parameter_listen_subject_only_if_include.foo", {})
    assert response["data"] == 2

    response = client.request("test_parameter_listen_subject_only_if_include.bar", {})
    assert response["data"] == 3

    with pytest.raises(OSError):
        client.request("test_parameter_listen_subject_only_if_include.start", {})
