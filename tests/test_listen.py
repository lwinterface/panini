from anthill.utils.helper import start_process

from anthill.sandbox import Sandbox
from anthill import app as ant_app


def run_anthill():
    app = ant_app.App(
        service_name='test_listen',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
    )

    @app.listen('foo')
    async def topic_for_requests(topic, message):
        return {'data': message['data'] + 1}

    @app.listen('foo.*.bar')
    async def composite_topic_for_requests(topic, message):
        return {'data': topic + str(message['data'])}

    app.start()


# run app as separate process - for testing it
start_process(run_anthill)

sandbox = Sandbox()


def test_listen_simple_topic_with_response():
    response = sandbox.request('foo', {'data': 1})
    assert response['data'] == 2
    assert 'isr-id' in response  # will be present in each response


def test_listen_composite_topic_with_response():
    topic1 = 'foo.some.bar'
    topic2 = 'foo.another.bar'
    response1 = sandbox.request(topic1, {'data': 1})
    response2 = sandbox.request(topic2, {'data': 2})
    assert response1['data'] == f'{topic1}1'
    assert response2['data'] == f'{topic2}2'
    assert 'isr-id' in response1
    assert 'isr-id' in response2
