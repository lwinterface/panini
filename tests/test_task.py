import pytest

from panini.test_client import TestClient, get_logger_files_path
from panini import app as panini_app

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_task",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_logger_files_path(),
    )

    @app.task()
    async def publish():
        await app.publish(subject="test_task.foo", message={"data": 1})

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_task.foo")
    def foo_listener(msg):
        global_object.public_variable = msg.data["data"] + 1

    client.start()
    yield client
    client.stop()


def test_task(client):
    assert global_object.public_variable == 0
    client.wait(1)
    assert global_object.public_variable == 2
