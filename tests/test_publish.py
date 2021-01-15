import time

from anthill.sandbox import Sandbox
from anthill import app as ant_app

from tests.global_object import Global


from anthill.utils.helper import start_process


def run_anthill():
    app = ant_app.App(
        service_name='test_publish',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.listen('foo')
    async def publish(topic, message):
        await app.aio_publish({'data': 1}, topic='bar')

    app.start()


global_object = Global()


sandbox = Sandbox()


@sandbox.handler('bar')
def bar_handler1(topic, message):
    global_object.public_variable = message['data']


@sandbox.handler('bar')
def bar_handler2(topic, message):
    global_object.another_variable = message['data'] + 1


# should be placed after sandbox.handler
start_process(run_anthill)


def test_publish_no_message():
    assert global_object.public_variable == 0
    assert global_object.another_variable == 0
    sandbox.publish('foo', {})
    sandbox.wait(2)  # wait for 2 messages
    assert global_object.public_variable == 1
    assert global_object.another_variable == 2
