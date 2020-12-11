from anthill import app as ant_app

app = ant_app.App(
    service_name='async_reply_to',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

log = app.logger

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}


@app.task()
async def request_to_another_topic():
    for _ in range(10):
        await app.aio_publish_request_with_reply_to_another_topic(msg,
                                                                  topic='some.topic.for.request.with.response.to'
                                                                        '.another.topic',
                                                                  reply_to='reply.to.topic')
        log.warning('sent request')


@app.listen('some.topic.for.request.with.response.to.another.topic')
async def topic_for_requests_listener(topic, message):
    log.warning('request has been processed')
    return {'success': True, 'data': 'request has been processed'}


@app.listen('reply.to.topic')
async def another_topic_listener(topic, message):
    log.warning(f'received response: {topic} {message}')


if __name__ == "__main__":
    app.start()
