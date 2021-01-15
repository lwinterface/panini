from anthill.sandbox import Sandbox
from tests.global_object import Global


sandbox = Sandbox()


global_object = Global()


@sandbox.handler('foo')
def foo_handler(topic, message):
    global_object.public_variable = message['data'] + 1


def test_sandbox_handler():
    sandbox.publish('foo', {'data': 1})
    sandbox.wait(count=1)

    assert global_object.public_variable == 2
