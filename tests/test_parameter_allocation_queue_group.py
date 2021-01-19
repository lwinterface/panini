import time
import pytest

from anthill.test_client import TestClient
from anthill import app as ant_app

from anthill.utils.helper import start_process


def run_anthill1():
    app = ant_app.App(
        service_name='test_allocation_queue_group1',
        host='127.0.0.1',
        port=4222,
        allocation_quenue_group="group1",
        app_strategy='asyncio',
        logger_required=False,
    )

    @app.listen('foo')
    async def foo(topic, message):
        return {'data': 1}

    app.start()


def run_anthill2():
    app = ant_app.App(
        service_name='test_allocation_queue_group2',
        host='127.0.0.1',
        port=4222,
        allocation_quenue_group="group1",
        app_strategy='asyncio',
        logger_required=False,
    )

    @app.listen('foo')
    async def foo(topic, message):
        return {'data': 2}

    app.start()


# if you want to run more that 1 anthill app in testing, please use start_process function for each app
start_process(run_anthill1)
start_process(run_anthill2)

# wait for anthill apps to setup
time.sleep(0.2)

# after that, no need to run client.start(), because anthill already running
client = TestClient()


def test_listen_topic_only_if_include_one_request():
    response = client.request('foo', {})
    assert response['data'] in (1, 2)


def test_listen_topic_only_if_include_multiple_requests():
    """Tests that some requests are handled by first anthill app and some by second"""
    results = set(client.request('foo', {})['data'] for _ in range(10))
    assert 1 in results
    assert 2 in results
