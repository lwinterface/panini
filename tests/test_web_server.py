import json

from aiohttp import web
from anthill import app as ant_app
from anthill.test_client import TestClient


def run_anthill():

    app = ant_app.App(
        service_name='test_web_server',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
        web_server=True,
        logger_required=False,
    )

    @app.listen('foo')
    async def foo(topic, message):
        message['data'] += 1
        return message

    @app.http.post('/bar')
    async def post_listener(request):
        data = await request.json()
        data['data'] += 2
        return web.json_response(data)

    app.start()


# provide parameter for using web_server - use_web_server; for waiting for web_server setup - sleep_time;
client = TestClient(run_anthill=run_anthill, use_web_server=True).start(sleep_time=1)


def test_request_and_post():
    response = {'data': 0}
    for i in range(5):
        response = client.request('foo', message={'data': response['data']})
        response = client.http_session.post('bar', data=json.dumps({'data': response['data']}))
        assert response.status_code == 200, response.text
        response = response.json()
        assert response['data'] == 3 * (i + 1)
