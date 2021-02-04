from anthill.test_client import TestClient
from anthill import app as ant_app

from tests.global_object import Global


def run_anthill():
    app = ant_app.App(
        service_name="test_publish",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_required=False,
    )

    @app.listen("foo")
    async def publish(topic, message):
        await app.aio_publish({"data": 1}, topic="bar")

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen("bar")
def bar_listener1(topic, message):
    global_object.public_variable = message["data"]


@client.listen("bar")
def bar_listener2(topic, message):
    global_object.another_variable = message["data"] + 1


# should be placed after all @client.listen
client.start()


def test_publish_no_message():
    assert global_object.public_variable == 0
    assert global_object.another_variable == 0
    client.publish("foo", {})
    client.wait(2)  # wait for 2 messages
    assert global_object.public_variable == 1
    assert global_object.another_variable == 2
