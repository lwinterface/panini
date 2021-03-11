import os
from panini import app as panini_app

app = panini_app.App(
    service_name="microservice1",
    host="nats-server" if "HOSTNAME" in os.environ else "127.0.0.1",
    port=4222,
    app_strategy="asyncio",
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


@app.timer_task(interval=1)
async def publish_periodically():
    for _ in range(10):
        await app.publish(subject="some.publish.subject", message=msg)
        log.warning(f"send message from periodic task {msg}")


if __name__ == "__main__":
    app.start()
