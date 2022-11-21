import pytest

from panini.exceptions import MessageSchemaError
from panini.test_client import TestClient
from panini import app as panini_app
from .helper import Global



def run_panini():
    app = panini_app.App(
        service_name="test_serializer_callable",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    def callable_validator(**message):
        if type(message) is not dict:
            raise MessageSchemaError("type(data) is not dict")
        if "data" not in message:
            raise MessageSchemaError("'data' not in message")
        if type(message["data"]) is not int:
            raise MessageSchemaError("type(message['data']) is not int")
        if message["data"] < 0:
            raise MessageSchemaError(f"Value of field 'data' is {message['data']} that negative")
        message["data"] += 1
        return message

    @app.listen("test_validator.foo", data_type=callable_validator)
    async def publish(msg):
        return {"success": True}

    @app.listen("test_validator.foo-with-error-cb", data_type=callable_validator)
    async def publish(msg):
        return {"success": True}

    @app.listen("test_validator.check")
    async def check(msg):
        try:
            callable_validator(**msg.data)
        except MessageSchemaError:
            return {"success": False}

        return {"success": True}

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini).start()
    yield client
    client.stop()


def test_no_message(client):
    assert not client.request("test_validator.check", {})["success"]


def test_incorrect_message(client):
    assert not client.request("test_validator.check", {"data": "string"})["success"]


def test_correct_message(client):
    assert client.request("test_validator.check", {"data": 1})["success"]


def test_request_with_correct_message(client):
    response = client.request("test_validator.foo", {"data": 1})
    assert response["success"] is True


def test_request_with_incorrect_message(client):
    response = client.request("test_validator.foo", {"data": "string"})
    assert (
        response["success"] is False
    )


def test_request_with_incorrect_message_error_cb(client):
    response = client.request("test_validator.foo-with-error-cb", {"notdata": "string"})
    assert response["success"] is False
    assert "error" in response
    assert "MessageSchemaError" in response["error"]

