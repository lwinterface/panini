import pytest

from panini.async_test_client import AsyncTestClient


def run_panini():
    from tests.async_test_client.separate_file.main import app
    app.start()


@pytest.fixture
async def client():
    client = await AsyncTestClient(run_panini).start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_request(client: AsyncTestClient):
    subject = "separate_file.async_test_client.listen_request"
    response = await client.request(subject, {})
    assert response["success"] is True
    assert response["message"] == subject
