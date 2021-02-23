import pytest

from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_anthill():
    app = ant_app.App(
        service_name="test_task",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.task()
    async def publish():
        await app.publish(topic="foo", message={"data": 1})

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen("foo")
def foo_listener(topic, message):
    global_object.public_variable = message["data"] + 1


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_task():
    assert global_object.public_variable == 0
    client.wait(1)
    assert global_object.public_variable == 2
