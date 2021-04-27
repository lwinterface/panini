import pytest

from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_listen",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_listen.foo")
    async def subject_for_requests(msg):
        return {"data": msg.data["data"] + 1}

    @app.listen("test_listen.foo.*.bar")
    async def composite_subject_for_requests(msg):
        return {"data": msg.subject + str(msg.data["data"])}

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)
    client.start()
    yield client
    client.stop()


def test_listen_simple_subject_with_response(client):
    response = client.request("test_listen.foo", {"data": 1})
    assert response["data"] == 2


def test_listen_composite_subject_with_response(client):
    subject1 = "test_listen.foo.some.bar"
    subject2 = "test_listen.foo.another.bar"
    response1 = client.request(subject1, {"data": 1})
    response2 = client.request(subject2, {"data": 2})
    assert response1["data"] == f"{subject1}1"
    assert response2["data"] == f"{subject2}2"
