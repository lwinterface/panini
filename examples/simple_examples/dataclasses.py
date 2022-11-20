import asyncio
from panini import app as panini_app

papp = panini_app.App(
    service_name="validators",
    host="127.0.0.1",
    port=4222,
)
from pydantic import BaseModel

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
    key7: int
    key8: int


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
async def publish():
    for _ in range(10):
        await papp.publish(subject="some.publish.subject", message=message)


# @app.timer_task(interval=2)
# async def publish_periodically():
#     for _ in range(10):
#         dataclass_message =
#         await app.publish(subject="some.publish.subject", message=message)




@papp.listen("some.publish.subject", data_type=TestMessage)
async def requests_listener(msg):
    log.info(f"got message {msg.data}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    papp.start()
