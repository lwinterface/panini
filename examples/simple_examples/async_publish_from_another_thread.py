from panini import app as panini_app
from panini.utils.helper import start_thread

app = panini_app.App(
    service_name="async_publish",
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


@app.timer_task(interval=2)
async def publish_periodically():
    start_thread(another_thread_func)


def another_thread_func():
    for _ in range(10):
        app.connector.publish_from_another_thread(
            subject="some.publish.subject", message=message
        )


@app.listen("some.publish.subject")
async def receive_messages(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")


if __name__ == "__main__":
    app.start()
