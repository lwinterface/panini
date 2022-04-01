import asyncio
import time
import pytest
from tests.helper import Global
from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_reply_to",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_long_tasks.start")
    async def reply_to(msg):
        await app.publish(
            message={"data": 1},
            subject="test_long_tasks.long_task",
            reply_to="test_long_tasks.result",
        )

    @app.listen("test_long_tasks.long_task")
    async def long_task(msg):
        await asyncio.sleep(5)
        msg.data["data"] += 2
        msg.data['t'] = time.time()
        return msg.data

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_long_tasks.result")
    def bar_listener(msg):
        global_object.public_variable = msg.data["data"] + 3
        global_object.list_variable.append(msg.data["t"])

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_long_tasks(client):
    assert global_object.public_variable == 0
    for _ in range(10):
        client.publish("test_long_tasks.start", {})
    time.sleep(5)
    client.wait(10)  # wait for bar_listener call
    assert global_object.public_variable == 6
    time_delta = max(global_object.list_variable) - min(global_object.list_variable)
    assert time_delta < 1