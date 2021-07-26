# Panini
  
Panini is a modern framework for fast and straightforward microservices development. Our goal is to create fastapi/aiohttp/flask-like solution but for NATS streaming.
 
The framework allows you to work with NATS features and some additional logic using a simple interface:
*  easy to initialize application
```python
from panini import app as panini_app

app = panini_app.App(
        service_name='your-microservice-name',
        host='127.0.0.1',
        port=4222,
)
```
*  stream via NATS broker to some subject

```python
@app.single()
async def publish():
    while True:
        message = get_some_update()
        await app.publish(subject='some.subject', message=message)
```
*  subscribe to subject
```python
@app.listen('some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```
*  request to subject
```python
response = await app.request(subject='some.request.subject.123', message={'request':'params'})
```
* receive a request from another microservice and return a response like HTTP request-response
```python
@app.listen('some.request.subject.123')
async def request_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle request
    return {'success': True, 'data': 'request has been processed'}
```
* create periodic tasks

```python
@app.interval(interval=2)
async def your_periodic_task():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message={'some': 'data'})
```
* synchronous and asynchronous endpoints

```python
@app.interval(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(subject='some.publish.subject', message={'some': 'data'})
```
* accept different datatypes: dict, str, bytes

```python
@app.interval(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(subject='some.publish.subject', message=b'messageinbytesrequiresminimumoftimetosend',
                         data_type=bytes)
```
* create middlewares for NATS messages

```python
from panini.middleware import Middleware

class MyMiddleware(Middleware):

    async def send_publish(self, subject, message, publish_func, **kwargs):
        print('do something before publish')
        await publish_func(subject, message, **kwargs)
        print('do something after publish')

    async def listen_publish(self, msg, cb):
        print('do something before listen')
        await cb(msg)
        print('do something after listen')

    async def send_request(self, subject, message, request_func, **kwargs):
        print('do something before send request')
        result = await request_func(subject, message, **kwargs)
        print('do something after send request')
        return result

    async def listen_request(self, msg, cb):
        print('do something before listen request')
        result = await cb(msg)
        print('do something after listen request')
        return result
```
* create HTTP endpoints with [aiohttp](https://github.com/aio-libs/aiohttp) and NATS endpoints all together in one microservice
```python
from aiohttp import web

@app.listen('some.publish.subject')
async def subject_for_requests_listener(msg):
    handle_incoming_message(msg.subject, msg.data)

@app.http.get('/get')
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    return web.Response(text="Hello, world")

@app.http.view('/path/to/rest/endpoints')
class MyView(web.View):
    """
    HTTP endpoints for REST schema
    """
    async def get(self):
        request = self.request
        return web.Response(text="Hello, REST world")

    async def post(self):
        request = self.request
        return web.Response(text="Hello, REST world")

```
* built-in traffic balancing between instances of the microservice if you have high loads
```python
app = panini_app.App(
        service_name='async_publish',
        host='127.0.0.1',
        allocation_queue_group='group24', 
        port=4222,
)

# incoming traffic will be distributed among 
# all microservices that are in the "group24"

```
What is NATS? 

It is a high-performance messaging system written in Golang. It is straightforward to use, can run millions of messages per minute through one broker, and easily scales if you need many brokers. Has 48 well-known clients, 11 of which are supported by maintainers, 18 are contributors to the community. Delivery Guarantees, High Availability and Fault Tolerance. Panini based on NATS python client.
 

What is subject? 

It is just a string of characters that form a name the publisher and subscriber can use to find each other. NATS supports a wild card that dramatically increases the usability of subjects

NATS support subject hierarchies and wildcards
 
What is a hierarchy? [here](https://docs.nats.io/nats-concepts/subjects#subject-hierarchies)

What is a wildcard? [here](https://docs.nats.io/nats-concepts/subjects#subject-hierarchies)

 
Just try following the examples to see how easy it is.

The project is inspired by faust, the wonderful python project based on Kafka Streams

## Documentation
is coming...

## Installing

```bash
pip install panini
```

Additional requirements:
- python >= 3.8.2

## Broker

Run broker from a directory that include file [docker-compose.yml](https://github.com/lwinterface/panini/blob/master/docker-compose.yml). Command below:
```bash
docker-compose up
```

Stop broker:
```bash
docker-compose down
```

Note, for production we recommend running the broker with dockerized microservices. Example of dockerized panini project [here](https://github.com/lwinterface/panini/examples/dockercompose_project)

## Examples

### Publish

For streams:

```python

from panini import app as panini_app

app = panini_app.App(
        service_name='async_publish',
        host='127.0.0.1',
        port=4222,
)

log = app.logger

msg = {'key1':'value1', 'key2':2, 'key3':3.0, 'key4':[1,2,3,4], 'key5':{'1':1, '2':2, '3':3, '4':4, '5':5}, 'key6':{'subkey1':'1', 'subkey2':2, '3':3, '4':4, '5':5}, 'key7':None}

@app.task()
async def publish():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message=msg)
        log.info(f'send message {msg}')


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message=msg)
        log.info(f'send message from periodic task {msg}')


@app.listen('some.publish.subject')
async def receive_messages(msg):
    log.info(f'got message {msg.data}')

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
from panini import app as panini_app

app = panini_app.App(
    service_name='async_request',
    host='127.0.0.1',
    port=4222,
)

log = app.logger

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}

@app.task()
async def request():
    for _ in range(10):
        result = await app.request(subject='some.request.subject.123', message=msg)
        log.info(f'response: {result}')

@app.listen('some.request.subject.123')
async def request_listener(msg):
    log.info('request has been processed')
    return {'success': True, 'data': f'request from {msg.subject} has been processed'}


if __name__ == "__main__":
    app.start()
```

### Request with response to another subject

A response of request is sent to the third subject. This method can significantly increase the throughput in comparison to classical request-response model

```python

from panini import app as panini_app

app = panini_app.App(
    service_name='async_reply_to',
    host='127.0.0.1',
    port=4222,
)

log = app.logger

msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}

@app.task()
async def request_to_another_subject():
    for _ in range(10):
        await app.publish(subject='some.subject.for.request.with.response.to.another.subject',
                          message=msg,
                          reply_to='reply.to.subject')
        log.info('sent request')

@app.listen('some.subject.for.request.with.response.to.another.subject')
async def request_listener(msg):
    log.info('request has been processed')
    return {'success': True, 'data': f'request from {msg.subject} has been processed'}

@app.listen('reply.to.subject')
async def another_subject_listener(msg):
    log.info(f'received response: {msg.subject} {msg.data}')


if __name__ == "__main__":
    app.start()

```

### Validators

Validator allows you to validate incoming messages:

```python

from panini import app as panini_app
from panini.validator import Validator, Field

app = panini_app.App(
    service_name='validators',
    host='127.0.0.1',
    port=4222,
)

log = app.logger


class SubTestValidator(Validator):
    subkey1 = Field(type=str)
    subkey2 = Field(type=int)


class TestValidator(Validator):
    key1 = Field(type=str)
    key2 = Field(type=int)
    key3 = Field(type=float)
    key4 = Field(type=list)
    key5 = Field(type=dict)
    key6 = Field(type=SubTestValidator)
    key7 = Field(type=int, null=True)
    key8 = Field(type=int, null=True, default=None)


msg = {'key1': 'value1', 'key2': 2, 'key3': 3.0, 'key4': [1, 2, 3, 4], 'key5': {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5},
       'key6': {'subkey1': '1', 'subkey2': 2, '3': 3, '4': 4, '5': 5}, 'key7': None}


@app.task()
async def publish():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message=msg)


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message=msg)


@app.listen('some.publish.subject', validator=TestValidator)
async def subject_for_requests_listener(msg):
    log.info(f'got message {msg.data}')


if __name__ == "__main__":
    app.start()

```

### HTTP server

You must specify web_server=True to activate the web server. [Aiohttp](https://docs.python.org/3/library/asyncio.html) is used as a web server. Accordingly, you can use their syntax.
Also, you can specify web

```python

from aiohttp import web
from panini import app as panini_app

app = panini_app.App(
    service_name='async_web_server',
    host='127.0.0.1',
    port=4222,
    web_server=True,
    web_host='127.0.0.1',
    web_port=8999,
)

log = app.logger

@app.http.get('/get')
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    return web.Response(text="Hello, world")

@app.http.view('/path/to/rest/endpoints')
class MyView(web.View):
    """
    HTTP endpoints for REST schema
    """
    async def get(self):
        request = self.request
        return web.Response(text="Hello, REST world")

    async def post(self):
        request = self.request
        return web.Response(text="Hello, REST world")


if __name__ == "__main__":
    app.start()


```

## Logging

Panini creates a logfile folder in the project directory and stores all logs there. There are several ways to store your own logs there.

Logging from app object:

```python
from panini import app as panini_app
from panini.utils.logger import get_logger

app = panini_app.App(  # create app
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
)

log = app.logger  # create log handler
log = get_logger('ms_template_sync_by_lib')  # does exactly the same thing

log.info("some log")  # write log
log.warning("some warn log")
log.error("some error log")
log.exception("some exception log with automatic traceback logging")

```

Separated (after setting at the startup - you can get any registered logger with a get_logger function):

```python
from panini.utils.logger import get_logger

log = get_logger('some_logger_name')

log.warning("some log")  # write log

```

Panini uses logging in main process by default, but you can change it to speed-up application on the app creation:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    logger_in_separate_process=True,  # specify this option for logging in separate process
)

```

Panini let you to choose between default (recommended by developers) and custom logger configurations. If you want to
use custom logging config - just create `config/log_config.json` file with custom logger configuration at the app root.
Panini will automatically detect and set it. After that you can get your logger with `get_logger` function.

## Testing

We use [pytest](https://docs.pytest.org/en/stable/) for testing

To run tests (notice, that nats-server must be running on port 4222 for tests): 
```shell
pytest
```
 
## Contributing

Welcome contributor! We are looking developers to make Panini a great project.

Working on your first Pull Request? You can learn how from this *free* series, [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github).

Here's how you can help:

* suggest new updates or report about bug [here](https://github.com/lwinterface/panini/issues)
* review a [pull request](https://github.com/lwinterface/panini/pulls)
* fix an [issue](https://github.com/lwinterface/panini/issues)
* write a tutorial
* always follow by [this](https://github.com/firstcontributions/first-contributions) guide for your contributions

At this point, you're ready to make your changes! Feel free to ask for help :smile_cat:






