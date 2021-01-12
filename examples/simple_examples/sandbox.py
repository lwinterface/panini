from anthill.sandbox import Sandbox
from anthill import app as ant_app


app = ant_app.App(
    service_name='async_publish',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)


response = {'success': True, 'data': 'request has been processed'}


@app.listen('some.request.topic')
async def topic_for_requests_listener(topic, message):
    return response


sandbox = Sandbox(app)


def test_1():
    response_ = sandbox.publish_request(message={'message': 'message'}, topic='some.request.topic')
    assert response_['success'] == response['success']
    assert response_['data'] == response['data']
    assert 'isr-id' in response_


if __name__ == "__main__":
    test_1()
