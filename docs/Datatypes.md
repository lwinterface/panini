### Basics

Every project using a microservice architecture is unique and has different requirements for the message format of communication between microservices. For example, for systems in the e-commerce or fintech industry, JSON format might be appropriate, but if you need to make an audio stream, then you may prefer to work with raw bytes. Panini works with 3 data types of messages:

- JSON - default datatype
- Bytes
- String

To set a specific datatype, you need to set it as argument <span class="red">`data_type`</span> when sending messages:

```python
await app.publish(
          subject="some.data.in.bytes",
          message=b'23oesj2o4jrs93oijr9s3oijr02zoje01p92ek012sx01p2ke01pjz',
          data_type=bytes,
      )
```

or listening for messages:

```python
@app.listen("some.data.in.bytes", data_type=bytes)
async def receive_bytes(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")
```

If an incoming message to a microservice requires an answer, Panini expects the output type to be the same as the input type. For example:

```python
@app.listen("subject.for.request.in.bytes", data_type=bytes)
async def receive_bytes(msg):
    data = msg.data
	  result = some_process_of_request(data)
    validate_result_is_bytes(result)  # the result should be returned as bytes
    return result
```

The result should be returned as bytes, otherwise, Panini will raise an exception.

### One more example

JSON type transforms to python's dict inside an endpoint's function. In this case, all the elements of your dict should be capable of jsonfying in order to send a response.

Let's take a look at an example that includes a task that sends a message and 3 listeners that receive this message as different datatypes:

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

What is going on here:

1. The message template is a dict that can be transformed into JSON
2. <span class="red">`@app.task`</span> publishes data in string format to subject <span class="red">`"some.publish.subject"`</span>(jsonifyed data is a string)
3. The first <span class="red">`@app.listen`</span> receives this data as default datatype - transforms it to dict
4. The second <span class="red">`@app.listen`</span> receives the same data as a string
5. The third <span class="red">`@app.listen`</span> receives the same data as bytes
<div class="attention">
<p class="attention__emoji-icon">💡</p><p> All these datatypes are just representations at the Panini level. Eventually, Panini transforms data into bytes before sending it to NATS for any datatype. When another microservice receives this message, it also receives bytes then transforms it into the requested datatype in the endpoint function.</p>
</div>

String type is string only inside the endpoint's function. Eventually, a microservice sends bytes anyway.