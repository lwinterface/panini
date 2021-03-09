import time

import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_timer_task",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.timer_task(0.1)
    async def publish_periodically():
        await app.publish(subject="test_timer_task.foo", message={})

    app.start()


global_object = Global()


@pytest.fixture(scope="session")
def client():
    client = TestClient(run_panini)

    @client.listen("test_timer_task.foo")
    def foo_listener(subject, message):
        global_object.another_variable += 2

    client.start()
    return client


def test_timer_task(client):
    assert global_object.another_variable == 0
    client.wait(20)
    start_time = time.time()
    assert global_object.another_variable == 40
    client.wait(20)
    assert global_object.another_variable == 80
    assert time.time() - start_time >= 0.4
