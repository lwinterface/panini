import pytest

from panini.test_client import TestClient
from panini import app as panini_app

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_reply_to",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
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


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_reply_to.bar")
    def bar_listener(msg):
        global_object.public_variable = msg.data["data"] + 3

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_reply_to(client):
    assert global_object.public_variable == 0
    client.publish("test_reply_to.start", {})
    client.wait(1)  # wait for bar_listener call
    assert global_object.public_variable == 6
