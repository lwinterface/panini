from panini import app as panini_app
from panini.middleware import Middleware


app = panini_app.App(
    service_name="async_middleware",
    host="127.0.0.1",
    port=4222,
)

log = app.logger

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
        await app.publish(subject="some.publish.subject", message=message)
        log.info(f"send message {message}")


# @app.task(interval=2)
# async def request_periodically():
#     response = await app.request(subject="some.request.subject", message=message)
#     log.info(f"response message from periodic task: {response}")


@app.listen("some.publish.subject")
async def receive_messages(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")


@app.listen("some.request.subject")
async def receive_messages(msg):
    return {"success": True, "data": "some data you asked for"}


class MyMiddleware(Middleware):
    async def send_publish(self, subject, message, publish_func, *args, **kwargs):
        print("do something before publish")
        await publish_func(subject, message, *args, **kwargs)
        print("do something after publish")

    async def listen_publish(self, msg, cb):
        print("do something before listen")
        await cb(msg)
        print("do something after listen")

    async def send_request(self, subject, message, request_func, *args, **kwargs):
        print("do something before send request")
        result = await request_func(subject, message, *args, **kwargs)
        print("do something after send request")
        return result

    async def listen_request(self, msg, cb):
        print("do something before listen request")
        result = await cb(msg)
        print("do something after listen request")
        return result


if __name__ == "__main__":
    app.add_middleware(MyMiddleware)
    app.start()
