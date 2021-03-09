import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_reply_to",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("test_reply_to.start")
    async def reply_to(msg):
        await app.publish(
            message={"data": 1},
            subject="test_reply_to.foo",
            reply_to="test_reply_to.bar",
        )

    @app.listen("test_reply_to.foo")
    async def helper(msg):
        msg.data["data"] += 2
        return msg.data

    app.start()


client = TestClient(run_panini)

global_object = Global()


@client.listen("test_reply_to.bar")
def bar_listener(subject, message):
    global_object.public_variable = message["data"] + 3


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_reply_to():
    assert global_object.public_variable == 0
    client.publish("test_reply_to.start", {})
    client.wait(1)  # wait for bar_listener call
    assert global_object.public_variable == 6
