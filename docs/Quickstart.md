Panini is a modern framework for fast and straightforward microservices development. It's like fastapi/aiohttp/flask-like solution but for NATS streaming.  The framework allows you to work with NATS features and some additional logic using a simple interface:

- easy to initialize application

```python
from panini import app as panini_app

app = panini_app.App(
        service_name='some-microservice-name',
        host='127.0.0.1',
        port=4222,
)
```

- stream via NATS broker to some subject

```python
@app.task()
async def publish():
    while True:
        message = get_some_update()
        await app.publish(subject='some.subject', message=message)
```

- subscribe to subject

```python
@app.listen('some.subject')
async def subject_for_requests_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle incoming message
```

- request to subject

```python
response = await app.request(subject='some.request.subject.123', message={'request':'params'})
```

- receive a request from another microservice and return a response like HTTP request-response

```python
@app.listen('some.request.subject.123')
async def request_listener(msg):
    subject = msg.subject
    message = msg.data
    # handle request
    return {'success': True, 'data': 'request has been processed'}
```

- create periodic tasks

```python
@app.timer_task(interval=2)
async def your_periodic_task():
    for _ in range(10):
        await app.publish(subject='some.publish.subject', message={'some':'data'})
```

- synchronous and asynchronous endpoints

```python
@app.timer_task(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(subject='some.publish.subject', message={'some':'data'})
```

- accept different datatypes: dict, str, bytes

```python
@app.timer_task(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(subject='some.publish.subject', message=b'messageinbytesrequiresminimumoftimetosend', data_type=bytes)
```

- create middlewares for NATS messages

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

- create HTTP endpoints with [aiohttp](https://github.com/aio-libs/aiohttp) and NATS endpoints all together in one microservice

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

- built-in traffic balancing between instances of the microservice if you have high loads

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

More ready-to-run examples [here](https://github.com/lwinterface/panini/tree/master/examples)