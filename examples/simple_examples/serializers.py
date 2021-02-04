import asyncio
from anthill import app as ant_app
from anthill.serializer import Serializer, Field

app = ant_app.App(
    service_name="serializers",
    host="127.0.0.1",
    port=4222,
    app_strategy="asyncio",
)

log = app.logger


class SubTestSerializer(Serializer):
    subkey1 = Field(type=str)
    subkey2 = Field(type=int)


class TestSerializer(Serializer):
    key1 = Field(type=str)
    key2 = Field(type=int)
    key3 = Field(type=float)
    key4 = Field(type=list)
    key5 = Field(type=dict)
    key6 = Field(type=SubTestSerializer)
    key7 = Field(type=int, null=True)
    key8 = Field(type=int, null=True, default=None)


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
        await app.aio_publish(msg, topic="some.publish.topic")


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.aio_publish(msg, topic="some.publish.topic")


@app.listen("some.publish.topic", serializator=TestSerializer)
async def requests_listener(topic, message):
    log.warning(f"got message {message}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    app.start()
