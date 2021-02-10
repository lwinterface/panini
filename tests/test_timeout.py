import pytest

from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path


def run_anthill():
    app = ant_app.App(
        service_name="test_timeout",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("publish.request.not.existing.topic")
    async def publish_request(topic, message):
        return await app.request(topic="not-existing-topic", message={"data": 1})

    app.start()


client = TestClient(run_anthill).start()


def test_publish_request_timeout():
    with pytest.raises(OSError):
        client.request("publish.request.not.existing.topic", {})
