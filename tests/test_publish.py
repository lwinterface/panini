import pytest

from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path, Global


def run_anthill():
    app = ant_app.App(
        service_name="test_publish",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def publish(topic, message):
        app.logger.error("GOT HERE")
        await app.publish(topic="bar", message={"data": 1})

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen("bar")
def bar_listener1(topic, message):
    print("Got response")
    global_object.public_variable = message["data"]


@client.listen("bar")
def bar_listener2(topic, message):
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
