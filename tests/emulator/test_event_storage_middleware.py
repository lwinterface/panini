import time

import pytest

from panini.middleware.writer_emulator_middleware import WriterEmulatorMiddleware
from panini.test_client import TestClient
from panini import app as panini_app
from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_middleware",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_middleware.publish")
    async def publish(msg):
        try:
            await app.publish(
                subject="test_middleware.publish.response",
                message={"data": msg.data["data"] + 1},
            )
        except Exception:
            app.logger.exception("test_middleware.publish")

    @app.listen("test_middleware.request")
    async def request(msg):
        try:
            response = await app.request(
                subject="test_middleware.request.helper",
                message={"data": msg.data["data"]},
            )
            return {"data": response["data"] + 2}
        except Exception:
            app.logger.exception("test_middleware.request")

    @app.listen("test_middleware.request.helper")
    async def helper(msg):
        try:
            return {"data": msg.data["data"] + 2}
        except Exception:
            app.logger.exception("test_middleware.request.helper")

    @app.listen("test_middleware.listen.publish")
    async def request(msg):
        try:
            await app.publish(
                subject="test_middleware.listen.publish.response",
                message={"data": msg.data["data"] + 3},
            )
        except Exception:
            app.logger.exception("test_middleware.listen.publish")

    @app.listen("test_middleware.listen.request")
    async def request(msg):
        try:
            return {"data": msg.data["data"] + 4}
        except Exception:
            app.logger.exception("test_middleware.listen.request")

    folder = "../resources"
    app.add_middleware(WriterEmulatorMiddleware, folder=folder)
    app.start()


global_object = Global()


@pytest.fixture(scope="session")
def client():
    client = TestClient(run_panini)

    @client.listen("test_middleware.publish.response")
    def publish_listener(msg):
        pass

    @client.listen("test_middleware.listen.publish.response")
    def listen_publish_listener(msg):
        pass

    client.start(do_always_listen=False)
    return client


def test_send_publish_middleware(client):
    client.publish("test_middleware.publish", {"data": 1})
    client.wait(1)


def test_send_request_middleware(client):
    client.request("test_middleware.request", {"data": 2})


def test_listen_publish_middleware(client):
    client.publish("test_middleware.listen.publish", {"data": 3})
    client.wait(1)


def test_listen_request_middleware(client):
    client.request("test_middleware.listen.request", {"data": 4})


def test_sleep(client):
    time.sleep(2)
