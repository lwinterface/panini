import os
import time
import json

from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path

testing_logs_directory_path = get_testing_logs_directory_path(
    "logs_test_logs", remove_if_exist=True
)


def run_anthill():
    app = ant_app.App(
        service_name="test_logs_in_separate_process",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_required=True,
        logger_files_path=testing_logs_directory_path,
        logger_in_separate_process=True,
    )

    log = app.logger

    @app.listen("foo")
    async def topic_for_requests(topic, message):
        log.info(f"Got topic: {topic}", message=message)
        return {"success": True}

    @app.listen("foo.*.bar")
    async def composite_topic_for_requests(topic, message):
        log.error(f"Got topic: {topic}", message=message)
        return {"success": True}

    @app.listen("kill.logs")
    async def kill_logs(topic, message):
        app.logger_process.kill()
        return {"success": True}

    app.start()


client = TestClient(run_anthill).start(sleep_time=2, is_daemon=False)


def test_simple_log():
    response = client.request("foo", {"data": 1})
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
        assert data["message"] == "Got topic: foo"
        assert data["extra"]["message"]["data"] == 1


def test_listen_composite_topic_with_response():
    topic = "foo.some.bar"
    response = client.request(topic, {"data": 2})
    assert response["success"] is True

    # wait for log being written
    time.sleep(0.1)
    with open(os.path.join(testing_logs_directory_path, "errors.log"), "r") as f:
        data = json.loads(f.read())
        assert data["name"] == "test_logs_in_separate_process"
        assert data["levelname"] == "ERROR"
        assert data["message"] == f"Got topic: {topic}"
        assert data["extra"]["message"]["data"] == 2


def test_kill_logs():
    response = client.request("kill.logs", {})
    assert response["success"] is True
    client.anthill_process.kill()
