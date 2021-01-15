from anthill.sandbox import Sandbox
from tests.global_object import Global


sandbox = Sandbox()


global_object = Global()


@sandbox.handler('foo')
def foo_handler(topic, message):
    return {'data': message['data'] + 5}


def test_sandbox_response_handler():
    response = sandbox.request('foo', {'data': 1})

    assert response['data'] == 6
