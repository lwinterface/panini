from panini import app as panini_app
from panini.utils.logger import get_logger
from panini.middleware import Middleware


app = panini_app.App(
    service_name="async_publish",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
)

# that is equal to get_logger('async_publish')
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
        log.warning(f"send message {message}")


# @app.timer_task(interval=2)
# async def publish_periodically():
#     for _ in range(10):
#         await app.publish(subject="some.publish.subject", message=message)
        # log.warning(f"send message from periodic task {msg}")


@app.listen("some.publish.subject")
async def receive_messages(msg):
    log.warning(f"got subject {msg.subject}")
    log.warning(f"got message {msg.data}")


class MyMiddleware(Middleware):

    async def send_publish(self, topic, message, publish_func, **kwargs):
        #do something before
        print('something before publish')
        await publish_func(topic, message, **kwargs)
        #do something after
        print('something after publish')

    async def listen_publish(self, msg, cb):
        #do something before
        print('something before publish')
        await cb(msg)
        # do something after
        print('something after publish')
    #
    # async def send_request(self, topic, message, request_func, **kwargs):
    #     # do something before
    #     result = await request_func(topic, message, **kwargs)
    #     # do something after
    #     return result
    #
    # async def listen_request(self, msg, cb):
    #     # do something before
    #     result = cb(msg)
    #     # do something after
    #     return result



if __name__ == "__main__":
    app.add_middleware(MyMiddleware)
    app.start()
