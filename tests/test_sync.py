from anthill.sandbox import Sandbox
from anthill import app as ant_app


app = ant_app.App(
    service_name='test_listen',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
)


@app.listen('foo')
def topic_for_requests(_, message):
    return {'data': message['data'] + 1}


@app.listen('foo.*.bar')
def composite_topic_for_requests(topic, message):
    return {'data': topic + str(message['data'])}


def foo_handler(topic, message):
    global_object.public_variable = message['data']

listen_topics_callbacks = {
    'foo': [foo_handler]
}


sandbox = Sandbox(app)


def test_listen_simple_topic_with_response():
    response = sandbox.publish_request({'data': 1}, 'foo')
    assert response['data'] == 2
    assert 'isr-id' in response  # will be present in each response


def test_listen_composite_topic_with_response():
    topic1 = 'foo.some.bar'
    topic2 = 'foo.another.bar'
    response1 = sandbox.publish_request({'data': 1}, topic1)
    response2 = sandbox.publish_request({'data': 2}, topic2)
    assert response1['data'] == f'{topic1}1'
    assert response2['data'] == f'{topic2}2'
    assert 'isr-id' in response1
    assert 'isr-id' in response2