import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_diff_datatypes",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_diff_datatypes.listen.dict")
    async def listen_dict(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.listen.str", data_type=str)
    async def listen_dict(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.listen.bytes.helper", data_type=bytes)
    async def listen_dict(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.listen.bytes")
    async def listen_dict(msg):
        try:
            response = await app.request(
                "test_diff_datatypes.listen.bytes.helper", b"", response_data_type=bytes
            )
            return {"type": type(response).__name__}
        except Exception:
            app.logger.exception("test_diff_datatypes.listen.bytes")

    @app.listen("test_diff_datatypes.publish.dict.helper")
    async def listen_dict(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.publish.dict")
    async def publish_dict(msg):
        await app.publish(
            "test_diff_datatypes.publish.dict.helper",
            {},
            reply_to="test_diff_datatypes.publish.listener",
        )

    @app.listen("test_diff_datatypes.publish.str.helper", data_type=str)
    async def listen_str(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.publish.str")
    async def publish_str(msg):
        await app.publish(
            "test_diff_datatypes.publish.str.helper",
            "",
            reply_to="test_diff_datatypes.publish.listener",
        )

    @app.listen("test_diff_datatypes.publish.bytes.helper", data_type=bytes)
    async def listen_bytes(msg):
        return {"type": type(msg.data).__name__}

    @app.listen("test_diff_datatypes.publish.bytes")
    async def publish_bytes(msg):
        await app.publish(
            "test_diff_datatypes.publish.bytes.helper",
            b"",
            reply_to="test_diff_datatypes.publish.listener",
        )

    @app.listen("test_diff_datatypes.request.dict")
    async def request_dict(msg):
        response = await app.request("test_diff_datatypes.publish.dict.helper", {})
        return response

    @app.listen("test_diff_datatypes.request.str")
    async def request_str(msg):
        response = await app.request(
            "test_diff_datatypes.publish.str.helper", "", response_data_type=str
        )
        return {"type": type(response).__name__}

    @app.listen("test_diff_datatypes.request.bytes")
    async def request_bytes(msg):
        response = await app.request(
            "test_diff_datatypes.publish.bytes.helper", b"", response_data_type=bytes
        )
        return {"type": type(response).__name__}

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_diff_datatypes.publish.listener")
    def dict_listener(msg):
        global_object.public_variable = msg.data["type"]

    client.start(do_always_listen=False, use_error_middleware=False)
    yield client
    client.stop()


def test_listen_dict(client):
    response = client.request("test_diff_datatypes.listen.dict", {})
    assert response["type"] == "dict"


def test_listen_str(client):
    response = client.request("test_diff_datatypes.listen.str", "")
    assert response["type"] == "str"


def test_listen_bytes(client):
    response = client.request("test_diff_datatypes.listen.bytes", {})
    assert response["type"] == "bytes"


def test_publish_dict(client):
    client.publish("test_diff_datatypes.publish.dict", {})
    client.wait(1)
    assert global_object.public_variable == "dict"


def test_publish_str(client):
    client.publish("test_diff_datatypes.publish.str", {})
    client.wait(1)
    assert global_object.public_variable == "str"


def test_publish_bytes(client):
    client.publish("test_diff_datatypes.publish.bytes", {})
    client.wait(1)
    assert global_object.public_variable == "bytes"


def test_request_dict(client):
    response = client.request("test_diff_datatypes.request.dict", {})
    assert response["type"] == "dict"


def test_request_str(client):
    response = client.request("test_diff_datatypes.request.str", {})
    assert response["type"] == "str"


def test_request_bytes(client):
    response = client.request("test_diff_datatypes.request.bytes", {})
    assert response["type"] == "bytes"
