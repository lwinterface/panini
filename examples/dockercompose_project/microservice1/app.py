from anthill import app as ant_app

app = ant_app.App(
    service_name="microservice1",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
)

log = app.logger.log

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
        await app.publish(topic="some.publish.topic", message=msg)
        log(f"send message from periodic task {msg}")


if __name__ == "__main__":
    app.start()
