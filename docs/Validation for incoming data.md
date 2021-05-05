Panini allows to validate fields and data type of values for incoming JSON messages.

Let's say we want to send a message by `microservice_1` ten times per second, message:

```python
{
    "key1": "value1",
    "key2": 2,
    "key3": 3.024444412342342342,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}
```

Then receive it by `microservice_2` but validate that all message fields and value types are correct. 

Microservice_1:

```python
import json
from panini import  app as panini_app

app = panini_app.App(
        service_name='microservice_1',
        host='127.0.0.1',
        port=4222,
)

message = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.024444412342342342,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}

@app.timer_task(interval=1)
async def publish_periodically():
    for _ in range(10):
        await app.publish(
            subject="some.publish.subject", message=message)
        )

if __name__ == "__main__":
    app.start()
```

Microservice_2:

```python
import json
from panini import  app as panini_app

app = panini_app.App(
        service_name='microservice_2',
        host='127.0.0.1',
        port=4222,
)

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

@app.listen("some.publish.subject", validator=TestValidator)
async def requests_listener(msg):
    log.info(f"got message {msg.data}")
    await asyncio.sleep(1)

if __name__ == "__main__":
    app.start()
```

Validator model has to inherit Validator class, accepts python datatypes: 

- str
- int
- float
- list
- dict
- bool
- another validation model(SubTestValidator in example)

Each field additionally: 

- add default key/value if absent in incoming message
- allows None(null) type
- allows many expected type's objects in list, for example message:

```python
{
    "key1": [
               {"subkey1": "asdf1", "subkey2": 342},
               {"subkey1": "sdf1", "subkey2": 2},
               {"subkey1": "sdfsd1", "subkey2": 2}
            ]
}
```

validators:

```python
class SubTestValidator(Validator):
    subkey1 = Field(type=str)
    subkey2 = Field(type=int)

class TestValidator(Validator):
    key1 = Field(type=SubTestValidator, many=True) 
```

If incoming message doesn't pass validation, Panini raise ValidationError