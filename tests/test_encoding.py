import pytest

from anthill.testclient import TestClient
from anthill import app as ant_app


def run_anthill():
    app = ant_app.App(
        service_name='test_encoding',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.listen('foo')
    async def foo(topic, message):
        return {'len': len(message['data'])}

    @app.listen('helper.correct')
    async def helper(topic, message):
        return {'data': 'data'}

    @app.listen('helper.incorrect')
    async def helper(topic, message):
        return 'message not dict'

    @app.listen('message.incorrect')
    async def bar(topic, message):
        await app.aio_publish_request(topic='helper.correct', message='message not dict')
        return {'success': True}

    @app.listen('message.correct')
    async def bar(topic, message):
        await app.aio_publish_request(topic='helper.incorrect', message={'data': 'some data'})
        return {'success': True}

    @app.listen('correct')
    async def bar(topic, message):
        await app.aio_publish_request(topic='helper.correct', message={'data': 'some data'})
        return {'success': True}

    app.start()


# if no @client.listen are registered - you can run .start() just simply in chain
client = TestClient(run_anthill).start()


def test_encoding():
    response = client.request('foo', {'data': 'some correct data'})
    assert response['len'] == 17

    response = client.request('foo', {'data': 'не латинские символы'})
    assert response['len'] == 20


def test_correct_message_format():
    response = client.request('correct', {'data': 'some data'})
    assert response['success'] is True


def test_incorrect_message_format():
    with pytest.raises(OSError):
        client.request('message.correct', {'data': 'some data'})

    with pytest.raises(OSError):
        client.request('message.incorrect', {'data': 'some data'})
