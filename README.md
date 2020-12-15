# Anthill

Easy to work [asyncio](https://docs.python.org/3/library/asyncio.html) library based on [NATS python client](https://github.com/nats-io/nats.py).

The syntax makes it easy to create fast and flexible microservices that are ready to scale.
Just try to follow the examples and you will see how uncomplicated it is.

The project is inspired by the syntax of [faust](https://github.com/robinhood/faust), the wonderful python project based on [Kafka Streams](https://kafka.apache.org/documentation/streams/) 

## Documentation
is coming..

## Installing

```bash
pip install anthill
```

Additional requirements:
- docker >= 19.03.8

## Broker

Run broker from directory that include file [docker-compose.yml](https://github.com/lwinterface/anthill/blob/master/docker-compose.yml). Command below:
```bash
docker-compose up
```

Stop broker:
```bash
docker-compose down
```

Note, for production we recommend running the broker with dockerized microservices. Example of dockerized Anthill project [here](https://github.com/lwinterface/anthill/examples/dockercompose_project)

## Examples

### Publish

For streams:

```python

from anthill import app as ant_app

app = ant_app.App(
        service_name='async_publish',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
)

log = app.logger

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
async def publish():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log.warning(f'send message {msg}')


@app.timer_task(interval=2)
async def publish_pereodically():
    for _ in range(10):
        await app.aio_publish(msg, topic='some.publish.topic')
        log.warning(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
async def recieve_messages(topic, message):
    log.warning(f'got message {message}')

if __name__ == "__main__":
    app.start()

```

Let's say name of script above `app.py`. Be sure that broker is running and just execute:

```python
python3 app.py
```

It's all! Microservice launched

### Request

Classical request-response:

```python
from anthill import app as ant_app

app = ant_app.App(
    service_name='async_request',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
)

log = app.logger

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}

@app.task()
async def request():
    for _ in range(10):
        result = await app.aio_publish_request(msg, topic='some.request.topic.123')
        log.warning(f'response: {result}')

@app.listen('some.request.topic.123')
async def request_listener(topic, message):
    log.warning('request has been processed')
    return {'success': True, 'data': 'request has been processed'}


if __name__ == "__main__":
    app.start()
```

### Request with response to another topic

A response of request is sent to the third topic. This method can significantly increase the throughput in comparison to classical request-response model

```python

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
        await app.aio_publish_request_with_reply_to_another_topic(msg, topic='some.topic.for.request.with.response.to.another.topic', reply_to='reply.to.topic')
        log.warning('sent request')

@app.listen('some.topic.for.request.with.response.to.another.topic')
async def request_listener(topic, message):
    log.warning('request has been processed')
    return {'success': True, 'data': 'request has been processed'}

@app.listen('reply.to.topic')
async def another_topic_listener(topic, message):
    log.warning(f'recieved response: {topic} {message}')


if __name__ == "__main__":
    app.start()

```

### Serializers

Serializer allows you to validate incoming messages:

```python

from anthill import app as ant_app
from anthill.serializer import Serializer, Field

app = ant_app.App(
        service_name='serializers',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
)

log = app.logger

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
    log.warning(f'got message {message}')


if __name__ == "__main__":
    app.start()

```

### HTTP server

You must specify web_server=True to activate the web server. [Aiohttp](https://docs.python.org/3/library/asyncio.html) is used as a web server. Accordingly, you can use their syntax.
Also you can spacify web

```python

from aiohttp import web
from anthill import app as ant_app

app = ant_app.App(
    service_name='async_web_server',
    host='127.0.0.1',
    port=4222,
    app_strategy='asyncio',
    web_server=True,
    web_host='127.0.0.1',
    web_port=8999,
)

log = app.logger

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

Not familiar with asyncio? Try a synchronous implementation


```python

from anthill import app as ant_app

app = ant_app.App(
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
)
log = app.logger

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
def publish():
    for _ in range(10):
        app.publish(msg, topic='some.publish.topic')
        log.warning(f'send message {msg}')


@app.timer_task(interval=2)
def publish_pereodically():
    for _ in range(10):
        app.publish(msg, topic='some.publish.topic')
        log.warning(f'send message from pereodic task {msg}')


@app.listen('some.publish.topic')
def topic_for_requests_istener(topic, message):
    log.warning(f'got message {message}')

if __name__ == "__main__":
    app.start()
```
Remember, a synchronous app_strategy many times slower than an asynchronous one. It is designed for users who have no experience with asyncio. Sync implementation only useful for very lazy microservices

## Logging

Anthill creates a logfile folder in the project directory and stores all logs there. There are several ways to store your own logs there.

Logging from app object:
```python
from anthill import app as ant_app
from anthill.logger import get_logger

app = ant_app.App(  #create app
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
)

log = app.logger    # create log handler
log = get_logger('ms_template_sync_by_lib')  # does exactly the same thing

log.info("some log")         #write log
log.warning("some warn log")
log.error("some error log")
log.exception("some exception log with automatic traceback logging")

```

Separated (after setting at the startup - you can get any registered logger with get_logger funciton):

```python
from anthill.logger import get_logger

log = get_logger('some_logger_name')    

log.warning("some log")         #write log

```

Anthill uses logging in separate process by default to speed-up app, but you can change it on the app creation:
```python
from anthill import app as ant_app

app = ant_app.App( 
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
    log_in_separate_process=False, # specify this option for logging in main process
)

```

Anthill let you to choose between default (recommended by developers) and custom logger configurations. If you want to
use custom logging config - just create `config/log_config.json` file with custom logger configuration at the app root.
Anthill will automitacally detect and set it. After that you can get your logger with `get_logger` function.

## Testing

is coming..
 
## Contibuting

Welcome contributer! We are looking developers to make Anthill a great project.

Working on your first Pull Request? You can learn how from this *free* series, [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github).

Here's how you can help:

* suggest new updates or report about bug [here](https://github.com/lwinterface/anthill/issues)
* review a [pull request](https://github.com/lwinterface/anthill/pulls)
* fix an [issue](https://github.com/lwinterface/anthill/issues)
* write a tutorial
* always follow by [this](https://github.com/firstcontributions/first-contributions) guide for your contributions

At this point, you're ready to make your changes! Feel free to ask for help :smile_cat:






