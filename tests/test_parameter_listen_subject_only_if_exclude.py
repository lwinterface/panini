import pytest

from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_parameter_listen_subject_only_if_exclude",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )



    @app.listen("test_parameter_listen_subject_only_if_exclude.start")
    async def start(msg):
        return {"data": 1}

    @app.listen("test_parameter_listen_subject_only_if_exclude.foo")
    async def foo(msg):
        return {"data": 2}

    @app.listen("test_parameter_listen_subject_only_if_exclude.bar")
    async def start(msg):
        return {"data": 3}

    app.add_filters(exclude=["start"])
    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini).start()
    yield client
    client.stop()


def test_listen_subject_only_if_exclude(client):
    response = client.request("test_parameter_listen_subject_only_if_exclude.foo", {})
    assert response["data"] == 2

    response = client.request("test_parameter_listen_subject_only_if_exclude.bar", {})
    assert response["data"] == 3

    with pytest.raises(OSError):
        client.request("test_parameter_listen_subject_only_if_exclude.start", {})
