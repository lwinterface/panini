from anthill import app as ant_app

app = ant_app.App(
    service_name='ms_template_async_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

log = app.logger.log




msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}


@app.task()
async def request():
    for _ in range(10):
        result = await app.aio_publish_request(msg, topic='some.request.topic.123')
        log(result)
    return



@app.listen('some.request.topic.123')
async def topic_for_requests_listener(topic, message):
    return {'success': True, 'data': 'request has been processed'}


if __name__ == "__main__":
    app.start()
