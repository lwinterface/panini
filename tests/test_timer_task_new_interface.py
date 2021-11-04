import time

import pytest

from panini.test_client import TestClient
from panini import app as panini_app

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_timer_task",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.task(0.1)
    async def publish_periodically():
        await app.publish(subject="test_timer_task.foo", message={})

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_timer_task.foo")
    def foo_listener(msg):
        global_object.another_variable += 2

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_timer_task(client):
    assert global_object.another_variable == 0
    client.wait(20)
    # client.wait(20 * 100000)
    start_time = time.time()
    assert global_object.another_variable == 40
    client.wait(20)
    assert global_object.another_variable == 80
    assert time.time() - start_time >= 0.4
