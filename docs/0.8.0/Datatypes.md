### Working with Data Types in Panini

Panini allows you to work with various data types when sending and receiving messages. This can be beneficial in a microservice architecture, as you can use the right format for the task at hand. Panini supports the following data types:

- JSON 
- Dict (based on JSON) - default data type
- Dataclass (based on JSON)
- String
- Bytes

To set a specific data type, you need to set it as an argument <span class="red">`data_type`</span> when sending or listening for messages. 

For example, to send a message in String format, use the following code:

```python
await app.publish(
          subject="some.data.in.string",
          message="This is a string message",
          data_type=str,
      )
```

Or, to listen for incoming Bytes, use the following code:

```python
@app.listen("some.data.in.bytes", data_type=bytes)
async def receive_bytes(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")
```

You can also specify the `data_type` of the response from a request. For example:

```python
subject = "a.b.c"
message = {"param1": "value1"} 
 response: bytes = app.request(subject=subject, message=message, response_data_type=bytes) 
```

The result should be returned as bytes, otherwise, Panini will raise an exception.

#### One more example

JSON type transforms to Python's dict inside an endpoint's function. In this case, all elements of your dict should be capable of jsonfying in order to send a response.

Let's take a look at an example that includes a task that sends a message and 3 listeners that receive this message as different data types:

```python
import json
from panini import  app as panini_app

app = panini_app.App(
        service_name='quickstart-app',
        host='127.0.0.1',
        port=4222,
)

message = {
    "key4": "value1",
    "key7": 2,
    "key3": 3.024444412342342342,
    "key1": [1, 2, 3, 4],
    "key6": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key5": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key2": None,
}

@app.task(interval=1)
async def publish_string():
    some_string = json.dumps(message, sort_keys=True)
    for _ in range(10):
        await app.publish(
            subject="some.publish.subject", 
            message=some_string, 
            data_type=str,
        )

@app.listen("some.publish.subject")
async def receive_dict(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data} type: {type(msg.data)}")

@app.listen("some.publish.subject", data_type=str)
async def receive_string(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data} type: {type(msg.data)}")

@app.listen("some.publish.subject", data_type=bytes)
async def receive_bytes(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data} type: {type(msg.data)}")

if __name__ == "__main__":
    app.start()
```

Explanation of the code:

1. The message template is a dict which can be transformed into JSON
2. <span class="red">`@app.task`</span> publishes data in string format to the subject <span class="red">`"some.publish.subject"`</span> (jsonified data is a string)
3. The first <span class="red">`@app.listen`</span> receives this data as the default data type, transforming it into a dict
4. The second <span class="red">`@app.listen`</span> receives the same data as a string
5. The third <span class="red">`@app.listen`</span> receives the same data as bytes

<div class="attention">
<p class="attention__emoji-icon">💡</p><p> All these data types are just representations at the Panini level. Eventually, Panini transforms data into bytes before sending it to NATS for any data type. When another microservice receives this message, it also receives bytes which are then transformed into the requested data type in the endpoint function.</p>
</div>

String type is a string only inside the endpoint's function. Eventually, a microservice sends bytes anyway.

For an example of how to use Dataclasses, see [Data Serialization page](https://paniniapp.io/docs/getting-started/dataclasses).