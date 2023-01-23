In some cases, a NATS network is not enough for a microservice's requirements and engineers may need an HTTP web server within the microservice to create a gateway between HTTP and NATS spaces. To accomplish this, Panini uses [Aiohttp](https://github.com/aio-libs/aiohttp).

In order to run a HTTP server, you have to call <span class="red">`app.setup_web_server`</span> with host, port, and other parameters, such as <span class="red">`ssl_context`</span>, <span class="red">`shutdown_timeout`</span>, or <span class="red">`access_log`</span>. A sample microservice with an HTTP endpoint might look like this:

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

This uses <span class="red">`@app.http.get`</span> for HTTP. Panini uses Aiohttp under the hood, which means <span class="red">`@app.http`</span> is the same as <span class="red">`routes`</span> from Aiohttp. For example, the following code is the same:

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

is equal to:

```python
@app.http.get('/get')
async def handle_get(request):
    ...

@app.http.post('/post')
async def handle_post(request):
    ...

# no need to call 'app.router.add_routes(routes)'
```

Now, let's look at an example of how to build a little REST API in Panini:

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

This example demonstrates how to build a class-based view from Aiohttp. To learn more, we recommend checking its documentation: [https://docs.aiohttp.org/en/stable/web_quickstart.html#resource-views](https://docs.aiohttp.org/en/stable/web_quickstart.html#resource-views).

Finally, let's move on to WebSocket servers.