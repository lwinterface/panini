import pytest

from panini.test_client import TestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_encoding",
        host="127.0.0.1",
        port=4222,
        logger_in_separate_process=False,
    )

    @app.listen("test_encoding.foo")
    async def foo(msg):
        return {"len": len(msg.data["data"])}

    @app.listen("test_encoding.helper.correct")
    async def helper(msg):
        return {"data": "data"}

    @app.listen("test_encoding.helper.incorrect")
    async def helper(msg):
        return "message not dict"

    @app.listen("test_encoding.message.incorrect")
    async def bar(msg):
        await app.request(
            subject="test_encoding.helper.correct", message="message not dict"
        )
        return {"success": True}

    @app.listen("test_encoding.message.correct")
    async def bar(msg):
        await app.request(
            subject="test_encoding.helper.incorrect", message={"data": "some data"}
        )
        return {"success": True}

    @app.listen("test_encoding.correct")
    async def bar(msg):
        await app.request(
            subject="test_encoding.helper.correct", message={"data": "some data"}
        )
        return {"success": True}

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)
    client.start()
    yield client
    client.stop()


def test_encoding(client):
    response = client.request("test_encoding.foo", {"data": "some correct data"})
    assert response["len"] == 17

    response = client.request("test_encoding.foo", {"data": "не латинские символы"})
    assert response["len"] == 20


def test_correct_message_format(client):
    response = client.request("test_encoding.correct", {"data": "some data"})
    assert response["success"] is True


def test_incorrect_message_format(client):
    with pytest.raises(OSError):
        client.request("test_encoding.message.correct", {"data": "some data"})

    with pytest.raises(OSError):
        client.request("test_encoding.message.incorrect", {"data": "some data"})
