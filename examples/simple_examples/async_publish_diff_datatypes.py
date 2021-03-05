from panini import app as panini_app
from panini.utils.logger import get_logger

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


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.publish(subject="some.publish.subject", message=message)

@app.listen("some.publish.subject", data_type=str)
async def receive_messages(msg):
    log.warning(f"got subject {msg.subject}")
    log.warning(f"got message {msg.data}")

@app.listen("some.publish.subject", data_type=bytes)
async def receive_messages(msg):
    log.warning(f"got subject {msg.subject}")
    log.warning(f"got message {msg.data}")

if __name__ == "__main__":
    app.start()
