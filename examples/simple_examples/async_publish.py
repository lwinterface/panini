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
        log.warning(f"send message {msg}")


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.publish(topic="some.publish.topic", message=msg)
        log.warning(f"send message from periodic task {msg}")


@app.listen("some.publish.topic")
async def receive_messages(topic, message):
    log.warning(f"got message {message}")


if __name__ == "__main__":
    app.start()
