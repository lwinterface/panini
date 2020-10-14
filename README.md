# Anthill
Simple [asyncio](https://docs.python.org/3/library/asyncio.html) framework based on [NATS python client](https://github.com/nats-io/nats.py).

## Installing

```bash
pip install anthill
```
## Run broker

TODO

## Examples

### Publish

```python

from anthill import app as ant_app

app = ant_app.App(
        service_name='async_publish',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
)

log = app.logger.log

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
async def publish():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log(f'send message {msg}')


@app.timer_task(interval=2)
async def publish_pereodically():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
async def recieve_messages(topic, message):
    log(f'got message {message}')

if __name__ == "__main__":
    app.start()

```

### Request

```python
from anthill import app as ant_app

app = ant_app.App(
    service_name='async_request',
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
        log(f'response: {result}')

@app.listen('some.request.topic.123')
async def request_listener(topic, message):
    log('request has been processed')
    return {'success': True, 'data': 'request has been processed'}


if __name__ == "__main__":
    app.start()
```

### Request with response to another topic
```python

from anthill import app as ant_app

app = ant_app.App(
    service_name='async_reply_to',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

log = app.logger.log

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}

@app.task()
async def request_to_another_topic():
    for _ in range(10):
        await app.aio_publish_request_with_reply_to_another_topic(msg, topic='some.topic.for.request.with.response.to.another.topic', reply_to='reply.to.topic')
        log('sent request')


@app.listen('some.topic.for.request.with.response.to.another.topic')
async def topic_for_requests_istener(topic, message):
    log('request has been processed')
    return {'success': True, 'data': 'request has been processed'}


@app.listen('reply.to.topic')
async def another_topic_listener(topic, message):
    log(f'recieved response: {topic} {message}')


if __name__ == "__main__":
    app.start()

```

### Serializers

```python

from anthill import app as ant_app
from anthill.serializer import Serializer, Field

app = ant_app.App(
        service_name='serializers',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
)

log = app.logger.log

class SubTestSerializer(Serializer):
    subkey1 = Field(type=str)
    subkey2 = Field(type=int)

class TestSerializer(Serializer):
    key1 = Field(type=str)
    key2 = Field(type=int)
    key3 = Field(type=float)
    key4 = Field(type=list)
    key5 = Field(type=dict)
    key6 = Field(type=SubTestSerializer)
    key7 = Field(type=int, null=True)
    key8 = Field(type=int, null=True, default=None)

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
async def publish():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')

@app.timer_task(interval=2)
async def publish_pereodically():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')

@app.listen('some.publish.topic', serializator=TestSerializer)
async def topic_for_requests_istener(topic, message):
    log(f'got message {message}')


if __name__ == "__main__":
    app.start()

```

### HTTP server

```python

from aiohttp import web
from anthill import app as ant_app

app = ant_app.App(
    service_name='async_web_server',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
    web_server=True
)

log = app.logger.log

@app.http.get('/get')
async def web_endpoint_listener(request):
    '''
    Single HTTP endpoint
    '''
    return web.Response(text="Hello, world")

@app.http.view('/path/to/rest/endpoinds')
class MyView(web.View):
    '''
    HTTP endpoints for REST schema
    '''
    async def get(self):
        request = self.request
        return web.Response(text="Hello, REST world")

    async def post(self):
        request = self.request
        return web.Response(text="Hello, REST world")


if __name__ == "__main__":
    app.start()


```

### Sync example

```python

from anthill import app as ant_app

app = ant_app.App(
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
)
log = app.logger.log

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
def publish():
    for _ in range(10):
        app.publish(msg, topic='some.publish.topic')
        log(f'send message {msg}')


@app.timer_task(interval=2)
def publish_pereodically():
    for _ in range(10):
        app.publish(msg, topic='some.publish.topic')
        log(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
def topic_for_requests_istener(topic, message):
    log(f'got message {message}')

if __name__ == "__main__":
    app.start()
```
