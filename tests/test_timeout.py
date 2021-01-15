import time
import pytest

from anthill.testclient import TestClient
from anthill import app as ant_app

from anthill.utils.helper import start_process


def run_anthill():
    app = ant_app.App(
        service_name='test_timeout',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.listen('publish.request.not.existing.topic')
    async def publish_request(topic, message):
        return await app.aio_publish_request({'data': 1}, topic='not-existing-topic')

    app.start()


client = TestClient()

start_process(run_anthill)
time.sleep(0.1)


def test_publish_request_timeout():
    with pytest.raises(OSError):
        client.request('publish.request.not.existing.topic', {})
