# Panini
  
Panini is a python microframework based on the [nats.py](http://nats.py/) library. Its goal is to offer developers an easy way to create NATS microservices with a lower barrier of entry. It provides a specific template for creating microservices, similarly to FastAPI, Aiohttp, or Flask. Like all of the above frameworks, Panini has its design limits and edge cases. In the case that you become restricted by Panini's capabilities, we recommend switching to [nats.py](https://github.com/nats-io/nats.py).

[![docs](https://img.shields.io/static/v1?label=docs&message=docs&color=informational)](https://panini.technology/)
[![Build Status](https://circleci.com/gh/lwinterface/panini/tree/master.svg?style=shield)](https://circleci.com/gh/lwinterface/panini/?branch=main)
[![Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)](https://pypi.org/project/nats-py)
[![License Apache 2.0](https://img.shields.io/github/license/lwinterface/panini)](https://www.apache.org/licenses/LICENSE-2.0)

Panini was inspired by [Faust](https://github.com/robinhood/faust) project. 
## Documentation

Documentation is [here](https://panini.technology/).


## How to install

Before getting started make sure you have all the prerequisites installed:

```python
pip install panini
```


## A simple listener app example

A minimal app with one stream endpoint, one request endpoint, and one periodic task might look like this:

```python
from panini import app as panini_app

app = panini_app.App(
        service_name='listener_app',
        host='127.0.0.1',
        port=4222,
)

@app.listen("some.subject.for.request")
async def request_listener(msg):
    """ request endpoint """
    print(f"request {msg.data} from {msg.subject} has been processed")
    return {"success": True, "message": "request has been processed"}

@app.listen("some.subject.for.stream")
async def stream_listener(msg):
    """ stream endpoint """
    print(f"event {msg.data} from {msg.subject} has been processed")

if __name__ == "__main__":
    app.start()
```

What's going on here?

1. Imported Panini.
2. Initialized app. Created an instance of class App from module panini with any microservice name, NATS host, and port.
3. First <span class="red">`@app.listen`</span> registers the listening subject <span class="red">`"some.subject.for.request"`</span> with <span class="red">`request_listener`</span>. Every time this app receives a request addressed to <span class="red">`"some.subject.for.request"`</span>, the function <span class="red">`request_listener`</span> is called to process it, then it sends a return response back to an addressee.
4. Secondly <span class="red">`@app.listen`</span> register the listening subject <span class="red">`"some.subject.for.stream"`</span> with <span class="red">`stream_listener`</span>. Same as with <span class="red">`request_listener`</span> but without sending the result back.
5. <span class="red">`app.start()`</span> runs an app. No code under this command will ever be called.

Save the above code to file *listener*_*app.py.*


<aside>
💡 The current function expects only JSON formattable returns, dict or list. However, you can also specify it as string or bytes. More details about this in Datatypes section._

</aside>


Make sure that you have all prerequisites from Install. Open the terminal to run the app:

```python
> python3 listener_app.py
======================================================================================
Panini service connected to NATS..
id: 3
name: listener_app__non_docker_env_270377__75017

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================
```

That's it. Now let's create something that will generate messages.

## A simple app example that generates messages

Our goal here is to trigger endpoints from listener app above: 

- <span class="purple">"some.subject.for.request"</span>  - request something, receive response
- <span class="purple">"some.subject.for.stream"</span> - send some event without waiting for response

```python
from panini import app as panini_app

app = panini_app.App(
        service_name='sender_app',
        host='127.0.0.1',
        port=4222,
)

@app.task(interval=1)
async def request_periodically():
		message = {"data":"request1234567890"}
    response = await app.request(
        subject="some.subject.for.request", 
        message=message,
    )
    print(response)
		

@app.task(interval=1)
async def publish_periodically():
		message = {"data":"event1234567890"}
    await app.publish(
        subject="some.subject.for.stream", 
        message=message,
    )

if __name__ == "__main__":
    app.start()
```

What's new here:

1. First, <span class="red">`@app.task`</span> registers function <span class="red">`request_periodically`</span> to call it periodically at given interval, each 1 second in the example.
2. Function <span class="red">`app.request`</span> sends requests, asynchronously waits for a response.
3. The second <span class="red">`@app.task`</span> does the same as the first one but for publishing.
4. Function <span class="red">`app.publish`</span> sends a message like a request but without expecting any response. Fire and forget.

Save the code to new file *sender_app.py.*

Make sure that *listener_app.py* keeps running, then open a new terminal session to run the sender app:

```python
> python3 sender_app.py
======================================================================================
Panini service connected to NATS..
id: 3
name: sender_app__non_docker_env_270377__75017

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
{'success': True, 'message': 'request has been processed'}
```

Note that in the terminal session where you run *listener_app.py* you should see received requests and events:

```python
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
event {'data': 'event1234567890'} from some.subject.for.stream has been processed
request {'data': 'request1234567890'} from some.subject.for.request has been processed
```

## More possibilities

In the first example, we created an application that listens for messages, in the second example, an application that sends messages. Panini allows you to freely combine sending and receiving messages in one application. 

Let's check out what else you can do with Panini using a minimal interface:

- One-time tasks on start. Similar to the above periodic task but without <span class="red">`interval`</span> argument

```python
@app.task()
async def publish():
    while True:
        message = get_some_update()
        await app.publish(subject='some.subject', message=message)
```

- Synchronous endpoints

```python
@app.task(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(
            subject='some.publish.subject', 
            message={'some':'data'}
        )
```

- Accept different datatypes: dict, str, bytes

```python
@app.timer_task(interval=2)
def your_periodic_task():
    for _ in range(10):
        app.publish_sync(
            subject='some.publish.subject', 
            message=b'messageinbytestosend', 
            data_type=bytes
        )
```

- Create middlewares for NATS messages

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

- Create HTTP endpoints with [Aiohttp](https://github.com/aio-libs/aiohttp) and NATS endpoints all together in one microservice
    
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
    
- Built-in traffic balancing between instances of the microservice if you have high loads

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

Need more examples? Check [here](https://github.com/lwinterface/panini/tree/master/examples).
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






