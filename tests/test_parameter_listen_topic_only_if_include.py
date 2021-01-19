import pytest

from anthill.test_client import TestClient
from anthill import app as ant_app


def run_anthill():
    app = ant_app.App(
        service_name='test_listen_topic_only_if_include',
        host='127.0.0.1',
        port=4222,
        listen_topic_only_if_include=['foo', 'bar'],
        app_strategy='asyncio',
        logger_required=False,
    )

    @app.listen('start')
    async def start(topic, message):
        return {'data': 1}

    @app.listen('foo')
    async def foo(topic, message):
        return {'data': 2}

    @app.listen('bar')
    async def start(topic, message):
        return {'data': 3}

    app.start()


client = TestClient(run_anthill).start()


def test_listen_topic_only_if_include():
    response = client.request('foo', {})
    assert response['data'] == 2

    response = client.request('bar', {})
    assert response['data'] == 3

    with pytest.raises(OSError):
        client.request('start', {})
