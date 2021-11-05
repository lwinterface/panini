import pytest

from panini.middleware import Middleware
from panini.test_client import TestClient
from panini import app as panini_app
from .helper import Global


class AddMiddleware(Middleware):
    async def send_publish(self, subject: str, message, publish_func, *args, **kwargs):
        message["data"] += 1
        await publish_func(subject, message, *args, **kwargs)

    async def send_request(self, subject: str, message, request_func, *args, **kwargs):
        response = await request_func(subject, message, *args, **kwargs)
        response["data"] += 2
        return response

    async def listen_publish(self, msg, callback):
        msg.data["data"] += 3
        await callback(msg)

    async def listen_request(self, msg, callback):
        response = await callback(msg)
        response["data"] += 4
        return response


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

    app.add_middleware(AddMiddleware)
    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini, socket_timeout=200, listener_socket_timeout=200)

    @client.listen("test_middleware.publish.response")
    def publish_listener(msg):
        global_object.public_variable = msg.data["data"] + 1

    @client.listen("test_middleware.listen.publish.response")
    def listen_publish_listener(msg):
        global_object.another_variable = msg.data["data"] + 3

    client.start(do_always_listen=False)
    yield client
    client.stop()


def test_send_publish_middleware(client):
    client.publish("test_middleware.publish", {"data": 1})
    client.wait(1)
    assert global_object.public_variable == 7


def test_send_request_middleware(client):
    response = client.request("test_middleware.request", {"data": 2})
    assert response["data"] == 16


def test_listen_publish_middleware(client):
    client.publish("test_middleware.listen.publish", {"data": 3})
    client.wait(1)
    assert global_object.another_variable == 13


def test_listen_request_middleware(client):
    response = client.request("test_middleware.listen.request", {"data": 4})
    assert response["data"] == 12
