from anthill.test_client import TestClient
from anthill import app as ant_app

from tests.global_object import Global


def run_anthill():
    app = ant_app.App(
        service_name='test_task',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.task()
    async def publish():
        await app.aio_publish({'data': 1}, topic='foo')

    app.start()


global_object = Global()


client = TestClient(run_anthill)


@client.listen('foo')
def foo_listener(topic, message):
    global_object.public_variable = message['data'] + 1


client.start()


def test_task():
    assert global_object.public_variable == 0
    client.wait(1)
    assert global_object.public_variable == 2



