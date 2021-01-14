import time

from anthill.sandbox import Sandbox
from anthill import app as ant_app

from tests.global_object import Global


app = ant_app.App(
    service_name='test_publish',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)


@app.listen('foo')
async def publish(topic, message):
    await app.aio_publish({'data': 1}, topic='bar')


global_object = Global()


sandbox = Sandbox(app)


@sandbox.handler
def bar_handler(topic, message):
    global_object.public_variable = message['data']


def test_publish():
    assert global_object.public_variable == 0
    sandbox.subscribe(topic='bar', callback=bar_handler)
    sandbox.publish('foo', {})
    sandbox.wait(1)
    assert global_object.public_variable == 1
