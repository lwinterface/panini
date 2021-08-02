from panini import app as panini_app
from panini.middleware.debug_middleware import DebugMiddleware

app = panini_app.App(
    service_name="debug_middleware_example",
    host="127.0.0.1",
    port=4222,
)


message = {
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
        await app.request(subject="some.publish.subject", message=message)


@app.listen("some.publish.subject")
async def receive_messages(msg):
    return {"success": True}


if __name__ == "__main__":
    app.add_middleware(DebugMiddleware, log_level="info")
    app.start()
