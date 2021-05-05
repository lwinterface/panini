Panini supports 3 datatypes:

- dict
- str
- bytes

For example:

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

@app.timer_task(interval=1)
async def publish_periodically():
    for _ in range(10):
        await app.publish(
            subject="some.publish.subject", message=json.dumps(message, sort_keys=True), data_type=str
        )

@app.listen("some.publish.subject", data_type=str)
async def receive_messages(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")

@app.listen("some.publish.subject", data_type=bytes)
async def receive_messages(msg):
    log.info(f"got subject {msg.subject}")
    log.info(f"got message {msg.data}")

if __name__ == "__main__":
    app.start()
```

This feature allows to use custom `json.dumps` or non-json messages

#TODO example with video/voice stream to show bytes usage