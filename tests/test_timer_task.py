import time

from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_anthill():
    app = ant_app.App(
        service_name="test_timer_task",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.timer_task(0.1)
    async def publish_periodically():
        await app.publish(topic="foo", message={})

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen("foo")
def foo_listener(topic, message):
    global_object.another_variable += 2


client.start()


def test_timer_task():
    assert global_object.another_variable == 0
    client.wait(5)
    start_time = time.time()
    assert global_object.another_variable == 10
    client.wait(5)
    assert global_object.another_variable == 20
    assert time.time() - start_time >= 0.4
