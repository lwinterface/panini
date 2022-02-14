import pytest
from panini.async_test_client import AsyncTestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="async_test_client_test_panini",
        host="127.0.0.1",
        port=4222,
    )

    @app.listen("async_test_client.test_panini")
    async def listen(msg):
        helper_subject = "async_test_client.test_panini_helper"
        response = await app.request(helper_subject, {})
        assert response["success"] is True
        assert response["subject"] == helper_subject
        return {"success": True, "subject": msg.subject}

    app.start()


@pytest.fixture(scope="module")
async def client():
    client = AsyncTestClient(run_panini=run_panini)

    @client.listen("async_test_client.test_panini_helper")
    async def listen(msg):
        return {"success": True, "subject": msg.subject}

    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_listen(client):
    subject = "async_test_client.test_panini"
    response = await client.request(subject, {})
    assert response["success"] is True
    assert response["subject"] == subject


@pytest.mark.asyncio
async def test_second(client):
    subject = "async_test_client.test_panini"
    response = await client.request(subject, {})
    assert response["success"] is True
    assert response["subject"] == subject
