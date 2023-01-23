> **Note:** Since Panini v0.8.0 internal validator has been removed, if you need incoming message validation, we recommend using dataclasses.


Ensuring reliable communication between microservices is crucial for a system's reliability. To help with this, Panini v0.8.0 introduced dataclasses as a way to validate incoming messages. 

Panini uses dataclasses to check all fields and data types of values for incoming JSON messages. We’ve tested it mostly with [Pydantic](https://docs.pydantic.dev/) dataclasses and also with [Mashumaro](https://mashumaro.readthedocs.io/en/latest/).

To illustrate this, here is an example of a Panini application with dataclasses used to serialize incoming messages:

```python
import asyncio
from panini import app as panini_app
from pydantic import BaseModel

papp = panini_app.App(
    service_name="serializers",
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
```

For more information, read the [Pydantic validation documentation](https://docs.pydantic.dev/usage/validators/).

### Experimental: Custom incoming message serialization

Panini also supports any Callable object as a `data_type` for custom processing. Here is an example of how to use it:

```python
from panini.exceptions import MessageSchemaError
from panini import app as panini_app

app = panini_app.App(
    service_name="test_serializer_callable",
    host="127.0.0.1",
    port=4222,
)


def callable_validator(message):
    if type(message) is not dict:
        raise MessageSchemaError("type(data) is not dict")
    if "data" not in message:
        raise MessageSchemaError("'data' not in message")
    if type(message["data"]) is not int:
        raise MessageSchemaError("type(message['data']) is not int")
    if message["data"] < 0:
        raise MessageSchemaError(f"Value of field 'data' is {message['data']} that negative")
    message["data"] += 1
    return message


@app.listen("test_validator.foo", data_type=callable_validator)
async def publish(msg):
    return {"success": True}


@app.listen("test_validator.foo-with-error-cb", data_type=callable_validator)
async def publish(msg):
    return {"success": True}


@app.listen("test_validator.check")
async def check(msg):
    try:
        message = callable_validator(**msg.data)
    except MessageSchemaError:
        return {"success": False}

    return {"success": True}


if __name__ == "__main__":
    app.start()
```

Using a custom data_type to process messages is an experimental feature, so please use it with caution.