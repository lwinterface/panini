import pytest

from panini.exceptions import ValidationError
from panini.test_client import TestClient
from panini import app as panini_app
from panini.validator import Validator, Field
from .helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_validator",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    class DataValidator(Validator):
        data = Field(type=int)

    @app.listen("test_validator.foo", validator=DataValidator)
    async def publish(msg):
        return {"success": True}

    def validation_error_cb(msg, error):
        return {"success": False, "error": "validation_error_cb"}

    @app.listen("test_validator.foo-with-error-cb", validator=DataValidator, validation_error_cb=validation_error_cb)
    async def publish(msg):
        return {"success": True}

    @app.listen("test_validator.check")
    async def check(msg):
        try:
            DataValidator.validated_message(msg.data)
        except ValidationError:
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
    response = client.request("test_validator.foo", {"data": "string"})
    assert response["success"] is False


def test_request_with_incorrect_message(client):
    response = client.request("test_validator.foo", {"data": 1})
    assert (
        response["success"] is True
    )  # both should be success = True, validator do not stop the request


def test_request_with_incorrect_message_error_cb(client):
    response = client.request("test_validator.foo-with-error-cb", {"notdata": "string"})
    assert response["success"] is False
    assert "error" in response
    assert "validation_error_cb" in response["error"]

