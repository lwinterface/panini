import os
import time
import json

import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

testing_logs_directory_path = get_testing_logs_directory_path(
    "logs_test_logs", remove_if_exist=True
)


def run_panini():
    app = panini_app.App(
        service_name="test_logs_in_separate_process",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_required=True,
        logger_files_path=testing_logs_directory_path,
        logger_in_separate_process=True,
    )

    log = app.logger

    @app.listen("test_logs_in_separate_process.foo")
    async def subject_for_requests(msg):
        log.info(f"Got subject: {msg.subject}", message=msg.data)
        return {"success": True}

    @app.listen("test_logs_in_separate_process.foo.*.bar")
    async def composite_subject_for_requests(msg):
        log.error(f"Got subject: {msg.subject}", message=msg.data)
        return {"success": True}

    @app.listen("test_logs_in_separate_process.kill.logs")
    async def kill_logs(msg):
        app.logger_process.kill()
        return {"success": True}

    app.start()


client = TestClient(run_panini)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start(sleep_time=2, is_daemon=False)


def test_simple_log():
    response = client.request("test_logs_in_separate_process.foo", {"data": 1})
    assert response["success"] is True

    # wait for log being written
    time.sleep(0.1)
    with open(
        os.path.join(testing_logs_directory_path, "test_logs_in_separate_process.log"),
        "r",
    ) as f:
        data = json.loads(f.read())
        assert data["name"] == "test_logs_in_separate_process"
        assert data["levelname"] == "INFO"
        assert data["message"] == "Got subject: test_logs_in_separate_process.foo"
        assert data["extra"]["message"]["data"] == 1


def test_listen_composite_subject_with_response():
    subject = "test_logs_in_separate_process.foo.some.bar"
    response = client.request(subject, {"data": 2})
    assert response["success"] is True

    # wait for log being written
    time.sleep(0.1)
    with open(os.path.join(testing_logs_directory_path, "errors.log"), "r") as f:
        for last_line in f:
            pass
        data = json.loads(last_line)
        assert data["name"] == "test_logs_in_separate_process"
        assert data["levelname"] == "ERROR"
        assert data["message"] == f"Got subject: {subject}"
        assert data["extra"]["message"]["data"] == 2


def test_kill_logs():
    response = client.request("test_logs_in_separate_process.kill.logs", {})
    assert response["success"] is True
    client.panini_process.kill()
