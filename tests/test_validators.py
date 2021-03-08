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

    @app.listen("foo", validator=DataValidator)
    async def publish(msg):
        await app.publish(subject="bar", message={"data": 1})

    @app.listen("check")
    async def check(msg):
        try:
            DataValidator.validated_message(msg.data)
        except ValidationError:
            return {"success": False}

        return {"success": True}

    app.start()


global_object = Global()


client = TestClient(run_panini)


@client.listen("bar")
def bar_listener1(subject, message):
    global_object.public_variable = message["data"]


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_no_message():
    assert not client.request("check", {})["success"]


def test_incorrect_message():
    assert not client.request("check", {"data": "string"})["success"]


def test_correct_message():
    assert client.request("check", {"data": 1})["success"]


def test_publish_correct_message():
    assert global_object.public_variable == 0
    client.publish("foo", {"data": "string"})
    client.wait(1)
    assert global_object.public_variable == 1


def test_publish_incorrect_message():
    assert global_object.public_variable == 1
    client.publish("foo", {"data": 1})
    client.wait(1)
    assert global_object.public_variable == 1
