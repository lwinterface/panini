import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path, Global


def run_panini():
    app = panini_app.App(
        service_name="test_publish",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def publish(msg):
        app.logger.error("GOT HERE")
        await app.publish(subject="bar", message={"data": 1})

    app.start()


global_object = Global()


client = TestClient(run_panini)


@client.listen("bar")
def bar_listener1(subject, message):
    print("Got response")
    global_object.public_variable = message["data"]


@client.listen("bar")
def bar_listener2(subject, message):
    print("Got response")
    global_object.another_variable = message["data"] + 1


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_publish_no_message():
    assert global_object.public_variable == 0
    assert global_object.another_variable == 0
    client.publish("foo", {})
    client.wait(2)  # wait for 2 messages
    assert global_object.public_variable == 1
    assert global_object.another_variable == 2
