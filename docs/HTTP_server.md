In some cases a NATS network is not enough for microservice's requirements and engineers may need an HTTP web server in one microservice with NATS. For an HTTP server, Panini uses [Aiohttp](https://github.com/aio-libs/aiohttp). It might be useful if you need to handle HTTP requests from a frontend or other microservices to create a gateway between HTTP and NATS spaces.

In order to run a HTTP server you have to call <span class="red">`app.setup_web_server`</span> with host, port, and other parameters that you want to pass to Aiohttp, for example, <span class="red">`ssl_context`</span> , <span class="red">`shutdown_timeout`</span> or <span class="red">`access_log`</span>.

Panini microservice with HTTP endpoint might look like this:

```python
from aiohttp import web
from panini import  app as panini_app

app = panini_app.App(
        service_name='nats-microservice-that-also-http',
        host='127.0.0.1',
        port=4222,
)
app.setup_web_server(port=5000)

# NATS listeners & tasks

@app.http.get("/test")
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    return web.Response(text="Hello, HTTP world")

if __name__ == "__main__":
    app.start()
```

As you can see it uses <span class="red">`@app.http.get`</span> for HTTP.  Panini uses Aiohttp under the hood, in other words <span class="red">`@app.http`</span> is <span class="red">`routes`</span> from Aiohttp. Let's take a look at an example with some Aiohttp code(without Panini): 

```python
routes = web.RouteTableDef()

@routes.get('/get')
async def handle_get(request):
    ...

@routes.post('/post')
async def handle_post(request):
    ...

app.router.add_routes(routes)
```

Whats going on here:

1. Getting <span class="red">`routes`</span> object in the first line of code
2. <span class="red">`@routes.get('/get')`</span> bound to routes GET endpoint with URI <span class="red">`/get`</span>
3. <span class="red">`@routes.post('/post')`</span> bound to routes POST endpoint with URI <span class="red">`/post`</span>

For Panini, it's equal to:

```python
@app.http.get('/get')
async def handle_get(request):
    ...

@app.http.post('/post')
async def handle_post(request):
    ...

# no need to call 'app.router.add_routes(routes)'
```

1. <span class="red">`@app.http.get('/get')`</span> is the same as <span class="red">`@routes.get('/get')`</span>
2. <span class="red">`@app.http.post('/post')`</span> is the same as <span class="red">`@routes.post('/post')`</span>

You can also use the rest of the syntax of Aoihttp in Panini with <span class="red">`@app.http`</span> . In fact, Panini just creates an instance of Aiohttp inside, therefore <span class="red">`@app.http`</span>  is <span class="red">`web.RouteTableDef()`</span>  from Aiohttp. 

Let's check how to build a little REST API in Panini:

```python
from aiohttp import web
from panini import  app as panini_app

app = panini_app.App(
        service_name='nats-microservice-that-also-http-rest',
        host='127.0.0.1',
        port=4222,
)
app.setup_web_server(port=5000)

@app.timer_task(interval=2)  
async def publish():
    for _ in range(10):
        await app.publish(subject="some.publish.subject", message={'some':'message'})

@app.http.view("/path/to/rest/endpoints")
class MyView(web.View):
    """
    HTTP endpoints for REST schema
    """

    async def get(self):
        # request = self.request
        return web.Response(text="Hello, REST world")

    async def post(self):
        # request = self.request
        return web.Response(text="Hello, REST world")

if __name__ == "__main__":
    app.start()
```

This example demonstrates how to build a class-based view from Aiohttp. To know more about Aiohttp, we recommend checking its documentation: [https://docs.aiohttp.org/en/stable/web_quickstart.html#resource-views](https://docs.aiohttp.org/en/stable/web_quickstart.html#resource-views) 

That's it. Next step - WebSocket server.