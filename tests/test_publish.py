import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_publish",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_publish.foo")
    async def publish(msg):
        await app.publish(subject="test_publish.bar", message={"data": 1})

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_publish.bar")
    def bar_listener1(msg):
        global_object.public_variable = msg.data["data"]

    @client.listen("test_publish.bar")
    def bar_listener2(msg):
        global_object.another_variable = msg.data["data"] + 1

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_publish_no_message(client):
    assert global_object.public_variable == 0
    assert global_object.another_variable == 0
    client.publish("test_publish.foo", {})
    client.wait(2)  # wait for 2 messages
    assert global_object.public_variable == 1
    assert global_object.another_variable == 2
