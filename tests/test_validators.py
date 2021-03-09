import pytest

from panini.exceptions import ValidationError
from panini.test_client import TestClient
from panini import app as panini_app
from panini.validator import Validator, Field
from .helper import get_testing_logs_directory_path, Global


def run_panini():
    app = panini_app.App(
        service_name="test_validator",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    class DataValidator(Validator):
        data = Field(type=int)

    @app.listen("test_validator.foo", validator=DataValidator)
    async def publish(msg):
        await app.publish(subject="test_validator.bar", message={"data": 1})

    @app.listen("test_validator.check")
    async def check(msg):
        try:
            DataValidator.validated_message(msg.data)
        except ValidationError:
            return {"success": False}

        return {"success": True}

    app.start()


global_object = Global()


@pytest.fixture(scope="session")
def client():
    client = TestClient(run_panini)

    @client.listen("test_validator.bar")
    def bar_listener1(subject, message):
        global_object.public_variable = message["data"]

    client.start()
    return client


def test_no_message(client):
    assert not client.request("test_validator.check", {})["success"]


def test_incorrect_message(client):
    assert not client.request("test_validator.check", {"data": "string"})["success"]


def test_correct_message(client):
    assert client.request("test_validator.check", {"data": 1})["success"]


def test_publish_correct_message(client):
    assert global_object.public_variable == 0
    client.publish("test_validator.foo", {"data": "string"})
    client.wait(1)
    assert global_object.public_variable == 1


def test_publish_incorrect_message(client):
    assert global_object.public_variable == 1
    client.publish("test_validator.foo", {"data": 1})
    client.wait(1)
    assert global_object.public_variable == 1
