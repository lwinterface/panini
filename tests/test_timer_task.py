import time

from anthill.test_client import TestClient
from anthill import app as ant_app

from tests.global_object import Global


def run_anthill():
    app = ant_app.App(
        service_name='test_timer_task',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.timer_task(0.1)
    async def publish_periodically():
        await app.aio_publish({}, topic='foo')

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen('foo')
def foo_listener(topic, message):
    global_object.another_variable += 2


client.start()


def test_timer_task():
    assert global_object.another_variable == 0
    client.wait(5)
    start_time = time.time()
    assert global_object.another_variable == 10
    client.wait(5)
    assert global_object.another_variable == 20
    assert time.time() - start_time >= 0.4
