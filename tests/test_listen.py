import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path


def run_panini():
    app = panini_app.App(
        service_name="test_listen",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def subject_for_requests(msg):
        return {"data": msg.data["data"] + 1}

    @app.listen("foo.*.bar")
    async def composite_subject_for_requests(msg):
        return {"data": msg.subject + str(msg.data["data"])}

    app.start()


client = TestClient(run_panini)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_listen_simple_subject_with_response():
    response = client.request("foo", {"data": 1})
    assert response["data"] == 2


def test_listen_composite_subject_with_response():
    subject1 = "foo.some.bar"
    subject2 = "foo.another.bar"
    response1 = client.request(subject1, {"data": 1})
    response2 = client.request(subject2, {"data": 2})
    assert response1["data"] == f"{subject1}1"
    assert response2["data"] == f"{subject2}2"

