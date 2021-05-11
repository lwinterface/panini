If a NATS network is not enough for you and you need an HTTP web server in one microservice with NATS, I have to tell you Panini can do it. For HTTP, Panini uses [aiohttp] ([https://github.com/aio-libs/aiohttp](https://github.com/aio-libs/aiohttp)) as the web server. 

Panini microservice with HTTP endpoint, might look like below:

```python
from aiohttp import web
from panini import  app as panini_app

app = panini_app.App(
        service_name='nats-microservice-that-also-http',
        host='127.0.0.1',
        port=4222,
				web_server=True,
				web_host='127.0.0.1',
        web_port=5000,
)

# app logic, NATS listeners & tasks

@app.http.get("/test")
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    return web.Response(text="Hello, HTTP world")

if __name__ == "__main__":
    app.start()
```

Use the aiohttp syntax as a decorator after @app.http, for example aiohttp code:

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

For Panini it's equal to:

```python
@app.http.get('/get')
async def handle_get(request):
    ...

@app.http.post('/post')
async def handle_post(request):
    ...

# no need to call 'app.router.add_routes(routes)'
```

It works in the same way for all "routes" functions. Let's say you want to build little REST API in Panini:

```python
.from aiohttp import web
from panini import  app as panini_app

app = panini_app.App(
        service_name='nats-microservice-that-also-http-rest',
        host='127.0.0.1',
        port=4222,
				web_server=True,
				web_host='127.0.0.1',
        web_port=5000,
)

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

That's it. Next step - websocket server