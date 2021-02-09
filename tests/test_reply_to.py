from anthill.test_client import TestClient
from anthill import app as ant_app

from tests.global_object import Global


def run_anthill():
    app = ant_app.App(
        service_name="test_reply_to",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_required=False,
    )

    @app.listen("start")
    async def reply_to(topic, message):
        await app.publish(
            message={"data": 1}, topic="foo", reply_to="bar"
        )

    @app.listen("foo")
    async def helper(topic, message):
        message["data"] += 2
        return message

    app.start()


client = TestClient(run_anthill)

global_object = Global()


@client.listen("bar")
def bar_listener(topic, message):
    global_object.public_variable = message["data"] + 3


# should be placed after all @client.listen
client.start()


def test_reply_to():
    assert global_object.public_variable == 0
    client.publish("start", {})
    client.wait(1)  # wait for bar_listener call
    assert global_object.public_variable == 6
