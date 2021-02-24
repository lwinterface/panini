import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path


def run_panini():
    app = panini_app.App(
        service_name="test_encoding",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def foo(topic, message):
        return {"len": len(message["data"])}

    @app.listen("helper.correct")
    async def helper(topic, message):
        return {"data": "data"}

    @app.listen("helper.incorrect")
    async def helper(topic, message):
        return "message not dict"

    @app.listen("message.incorrect")
    async def bar(topic, message):
        await app.request(topic="helper.correct", message="message not dict")
        return {"success": True}

    @app.listen("message.correct")
    async def bar(topic, message):
        await app.request(topic="helper.incorrect", message={"data": "some data"})
        return {"success": True}

    @app.listen("correct")
    async def bar(topic, message):
        await app.request(topic="helper.correct", message={"data": "some data"})
        return {"success": True}

    app.start()


client = TestClient(run_panini)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_encoding():
    response = client.request("foo", {"data": "some correct data"})
    assert response["len"] == 17

    response = client.request("foo", {"data": "не латинские символы"})
    assert response["len"] == 20


def test_correct_message_format():
    response = client.request("correct", {"data": "some data"})
    assert response["success"] is True


def test_incorrect_message_format():
    with pytest.raises(OSError):
        client.request("message.correct", {"data": "some data"})

    with pytest.raises(OSError):
        client.request("message.incorrect", {"data": "some data"})
