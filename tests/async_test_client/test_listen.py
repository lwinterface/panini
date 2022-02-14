import asyncio
import pytest
from panini.async_test_client import AsyncTestClient


@pytest.fixture
def future():
    return asyncio.Future()


@pytest.fixture
async def client(future):
    client = AsyncTestClient()

    @client.listen("async_test_client.*")
    async def listen(msg):
        future.set_result({"listen": "success", "subject": msg.subject})

    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_listen(client, future):
    subject = "async_test_client.test_listen"
    await client.publish(subject, {})
    msg = await asyncio.wait_for(future, 1)
    assert msg["listen"] == "success"
    assert msg["subject"] == subject


@pytest.mark.asyncio
async def test_another_listen(client, future):
    subject = "async_test_client.test_another_listen"
    await client.publish(subject, {})
    msg = await asyncio.wait_for(future, 1)
    assert msg["listen"] == "success"
    assert msg["subject"] == subject
