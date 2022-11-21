import pytest
from panini.test_client import TestClient
from panini import app as panini_app
from pydantic import BaseModel, validator, ValidationError
from .helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_serializer_dacite",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )


    class DataSchema(BaseModel):
        data: int

        @validator('data')
        def validate_data_greater_then_zero(cls, v):
            if v < 0:
                raise ValueError(f"Value of field 'data' is {v} that negative")

    @app.listen("test_validator.foo", data_type=DataSchema)
    async def publish(msg):
        return {"success": True}

    @app.listen("test_validator.foo-with-error-cb", data_type=DataSchema)
    async def publish(msg):
        return {"success": True}

    @app.listen("test_validator.check")
    async def check(msg):
        try:
            DataSchema(**msg.data)
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

