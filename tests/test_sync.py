import time
from anthill.utils.helper import start_process

from anthill.testclient import TestClient
from anthill import app as ant_app

from tests.global_object import Global


def run_anthill():
    app = ant_app.App(
        service_name='test_sync',
        host='127.0.0.1',
        port=4222,
        app_strategy='sync',
    )

    @app.listen('foo')
    def topic_for_requests(topic, message):
        return {'data': message['data'] + 1}

    @app.listen('foo.*.bar')
    def composite_topic_for_requests(topic, message):
        return {'data': topic + str(message['data'])}

    @app.listen('publish')
    def publish(topic, message):
        app.publish(topic='publish.handler', message={'data': message['data'] + 1})

    @app.listen('publish.request')
    def publish_request(topic, message):
        response = app.publish_request(topic='publish.request.helper', message={'data': message['data'] + 1})
        app.publish(topic='publish.request.handler', message={'data': response['data'] + 3})

    @app.listen('publish.request.helper')
    def publish_request_helper(topic, message):
        return {'data': message['data'] + 2}

    @app.listen('publish.request.reply')
    def publish_request(topic, message):
        app.publish_request_with_reply_to_another_topic(topic='publish.request.reply.helper',
                                                        message={'data': message['data'] + 1},
                                                        reply_to='publish.request.reply.replier')

    @app.listen('publish.request.reply.helper')
    def publish_request_helper(topic, message):
        return {'data': message['data'] + 1}

    @app.listen('publish.request.reply.replier')
    def publish_request_helper(topic, message):
        app.publish(topic='publish.request.reply.handler', message={'data': message['data'] + 1})

    app.start()


client = TestClient()

global_object = Global()


@client.listen('publish.handler')
def publish_handler(topic, message):
    global_object.public_variable = message['data'] + 1


@client.listen('publish.request.handler')
def publish_request_handler(topic, message):
    global_object.another_variable = message['data'] + 4


@client.listen('publish.request.reply.handler')
def publish_request_reply_handler(topic, message):
    global_object.additional_variable = message['data'] + 1


# sync app creates more subprocesses, so it must not be daemon
process = start_process(run_anthill, daemon=False)
time.sleep(4)  # wait for sync app to setup


def test_listen_simple_topic_with_response():
    response = client.request('foo', {'data': 1})
    assert response['data'] == 2


def test_listen_composite_topic_with_response():
    topic1 = 'foo.some.bar'
    topic2 = 'foo.another.bar'
    response1 = client.request(topic1, {'data': 1})
    response2 = client.request(topic2, {'data': 2})
    assert response1['data'] == f'{topic1}1'
    assert response2['data'] == f'{topic2}2'


def test_publish():
    assert global_object.public_variable == 0
    client.publish('publish', {'data': 1})
    client.wait(1)
    assert global_object.public_variable == 3


def test_publish_request():
    assert global_object.another_variable == 0
    client.publish('publish.request', {'data': 0})
    client.wait(1)
    assert global_object.another_variable == 10


def test_publish_request_reply():
    assert global_object.additional_variable == 0
    client.publish('publish.request.reply', {'data': 0})
    client.wait(1)
    assert global_object.additional_variable == 4
    process.terminate()  # kill the app process in the last unittest
    # TODO: bug with 2 processes
