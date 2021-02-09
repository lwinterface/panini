from aiohttp import web
from anthill import app as ant_app

app = ant_app.App(
    service_name="async_web_server",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
    web_server=True,
)

log = app.logger

msg = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}


@app.task()
async def publish():
    for _ in range(10):
        await app.publish(topic="some.publish.topic", message=msg)


@app.timer_task(interval=2)
async def publish_periodically():
    await app.publish(topic="some.publish.topic", message=msg)


@app.listen("some.publish.topic")
async def topic_for_requests_listener(topic, message):
    log.warning(f"got message {message}")


@app.http.get("/get")
async def web_endpoint_listener(request):
    """
    Single HTTP endpoint
    """
    return web.Response(text="Hello, world")


@app.http.view("/path/to/rest/endpoints")
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
