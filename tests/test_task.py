import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_task",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.task()
    async def publish():
        await app.publish(subject="test_task.foo", message={"data": 1})

    app.start()


global_object = Global()


@pytest.fixture(scope="session")
def client():
    client = TestClient(run_panini)

    @client.listen("test_task.foo")
    def foo_listener(subject, message):
        global_object.public_variable = message["data"] + 1

    client.start()
    return client


def test_task(client):
    assert global_object.public_variable == 0
    client.wait(1)
    assert global_object.public_variable == 2
