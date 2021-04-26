import os
import json

import pytest

from panini.test_client import TestClient, get_logger_files_path
from panini import app as panini_app

testing_logs_directory_path = get_logger_files_path(
    "test_logger_logs", remove_if_exist=True
)


def run_panini():
    app = panini_app.App(
        service_name="test_logs",
        host="127.0.0.1",
        port=4222,
        logger_required=True,
        logger_in_separate_process=False,
    )

    log = app.logger

    @app.listen("test_logs.foo")
    async def subject_for_requests(msg):
        log.info(f"Got subject: {msg.subject}", message=msg.data)
        return {"success": True}

    @app.listen("test_logs.foo.*.bar")
    async def composite_subject_for_requests(msg):
        log.error(f"Got subject: {msg.subject}", message=msg.data)
        return {"success": True}

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini, logger_files_path=testing_logs_directory_path)
    client.start()
    yield client
    client.stop()


def test_simple_log(client):
    response = client.request("test_logs.foo", {"data": 1})
    assert response["success"] is True
    with open(os.path.join(testing_logs_directory_path, "test_logs.log"), "r") as f:
        data = json.loads(f.read())
        assert data["name"] == "test_logs"
        assert data["levelname"] == "INFO"
        assert data["message"] == "Got subject: test_logs.foo"
        assert data["extra"]["message"]["data"] == 1


def test_listen_composite_subject_with_response(client):
    subject = "test_logs.foo.some.bar"
    response = client.request(subject, {"data": 2})
    assert response["success"] is True
    with open(os.path.join(testing_logs_directory_path, "errors.log"), "r") as f:
        for last_line in f:
            pass
        data = json.loads(last_line)
        assert data["name"] == "test_logs"
        assert data["levelname"] == "ERROR"
        assert data["message"] == f"Got subject: {subject}"
        assert data["extra"]["message"]["data"] == 2
