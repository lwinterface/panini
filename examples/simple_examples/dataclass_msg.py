import asyncio
from panini import app as panini_app
from pydantic import BaseModel

papp = panini_app.App(
    service_name="validators",
    host="127.0.0.1",
    port=4222,
)


log = papp.logger


class SubTestData(BaseModel):
    subkey1: str
    subkey2: int

class TestMessage(BaseModel):
    key1: str
    key2: int
    key3: float
    key4: list
    key5: dict
    key6: SubTestData
    key7: int = None
    key8: int = None


message = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}


@papp.task()
async def publish_dataclass():
    for _ in range(10):
        message_dataclass = TestMessage(**message)
        await papp.publish(
            subject="some.publish.subject",
            message=message_dataclass
        )




@papp.listen("some.publish.subject", data_type=TestMessage)
async def receive_dataclass(msg):
    log.info(f"got message {msg.data}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    papp.start()
