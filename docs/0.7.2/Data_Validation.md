When many microservices communicate with each other, an essential consideration for reliability is ensuring that NATS client properly validates incoming messages. Engineers want to make sure that any data that enters an application is valid and secure.

Panini allows for checking all fields and data types of values for incoming JSON messages. Validator is very similar to Serializer in Django or Dataclasses. 

Example of validator:

```python
class CoctailValidator(Validator):
    id_ = Field(type=int)
    name = Field(type=str)
    price = Field(type=float)
    ingredients = Field(type=dict)
    history_of_orders = Field(type=list)
```

Validator can accept JSON data types or another validator if you need to validate data of a nested dictionary. 

Let's say we want to send a message by <span class="red">`microservice_1`</span> ten times per second, the message:

```python
{
    "key1": "value1",
    "key2": 2,
    "key3": 3.02444441234,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}
```

Then receive it by <span class="red">`microservice_2`</span> but validate that all message fields and value types are correct. 

<span class="red">`microservice_1`</span>:

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

@app.task(interval=1)
async def publish_periodically():
    for _ in range(10):
        await app.publish(
            subject="some.publish.subject", message=message)
        )

if __name__ == "__main__":
    app.start()
```

<span class="red">`microservice_2`</span>:

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

The validator model has to inherit Validator class. Acceptable python datatypes: 

- str
- int
- float
- list
- dict
- bool
- None
- another validation model(SubTestValidator in the example)

Each field optionally allows: 

- add default key/value if they are absent in incoming message
- allows None(null) type
- allows many nested objects in list, for example message:
    
    ```python
    {
        "key1": [
                   {"subkey1": "asdf1", "subkey2": 342},
                   {"subkey1": "sdf1", "subkey2": 2},
                   {"subkey1": "sdfsd1", "subkey2": 2}
                ]
    }
    ```
    
    Validators:
    
    ```python
    class SubTestValidator(Validator):
        subkey1 = Field(type=str)
        subkey2 = Field(type=int)
    
    class TestValidator(Validator):
        key1 = Field(type=SubTestValidator, many=True) 
    ```
    

If an incoming message doesn't pass validation, Panini will raise <span class="red">`ValidationError`</span>.

We consider the current data validation system as underdeveloped. If you feel a lack of features, you can always consider external solutions for this:

- [Dataclasses](https://docs.python.org/3/library/dataclasses.html)
- [Cerberus](https://docs.python-cerberus.org/en/stable/usage.html#basic-usage)
- [Colander](https://docs.pylonsproject.org/projects/colander/en/latest/)
- [Jsonschema](https://python-jsonschema.readthedocs.io/en/latest/)