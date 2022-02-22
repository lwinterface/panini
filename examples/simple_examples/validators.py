import asyncio
from panini import app as panini_app
from panini.validator import Validator, Field

app = panini_app.App(
    service_name="validators",
    host="127.0.0.1",
    port=4222,
)

log = app.logger


class SubTestValidator(Validator):
    subkey1 = Field(type=str)
    subkey2 = Field(type=int)


class TestValidator(Validator):
    key1 = Field(type=str)
    key2 = Field(type=int)
    key3 = Field(type=float)
    key4 = Field(type=list)
    key5 = Field(type=dict)
    key6 = Field(type=SubTestValidator)
    key7 = Field(type=int, null=True)
    key8 = Field(type=int, null=True, default=None)


message = {
    "key1": ["value1",],
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


@app.timer_task(interval=2)
async def publish_periodically():
    for _ in range(10):
        await app.publish(subject="some.publish.subject", message=message)


def validation_error_cb(msg, error):
    return {"success": False, "error": "validation_error_cb"}


@app.listen("some.publish.subject", validator=TestValidator, validation_error_cb=validation_error_cb)
async def requests_listener(msg):
    log.info(f"got message {msg.data}")
    await asyncio.sleep(1)


if __name__ == "__main__":
    app.start()
