import asyncio

import pytest

from panini.async_test_client import AsyncTestClient
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="async_test_client_test_error_handling",
        host="127.0.0.1",
        port=4222,
    )

    @app.listen("async_test_client.test_error_handling")
    async def listen(msg):
        error = 1 // 0
        return {"success": False if error else True}

    app.start()


@pytest.fixture
async def client():
    client = await AsyncTestClient(run_panini=run_panini).start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_error(client):
    subject = "async_test_client.test_error_handling"
    with pytest.raises(asyncio.TimeoutError):
        await client.request(subject, {})
