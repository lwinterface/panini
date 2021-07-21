import pytest

from panini.async_test_client import AsyncTestClient


@pytest.fixture
async def client():
    client = AsyncTestClient()

    @client.listen("async_test_client.test_request")
    async def listen(msg):
        return {"listen": "success", "subject": msg.subject}

    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_request(client: AsyncTestClient):
    subject = "async_test_client.test_request"
    response = await client.request(subject, {})
    assert response["listen"] == "success"
    assert response["subject"] == subject
