Since Panini switched from [asyncio-nats-client](https://pypi.org/project/asyncio-nats-client/) to [nats-py](https://pypi.org/project/nats-py/), it has become possible to support one of the most important features of NATS 2.0 - JetStream.

The major difference between **Core NATS** and **NATS JetStream** is that Core NATS is a stateless messaging protocol, meaning that it does not guarantee message delivery, while JetStream is an extension of Core NATS that allows you to store messages and replay in case of problems.

It is recommended to familiarize yourself with JetStream by reading the [NATS Concepts documentation](https://docs.nats.io/nats-concepts/jetstream). Additionally, you can read the [Grokking NATS Consumers blog post](https://www.byronruth.com/grokking-nats-consumers-part-1/) for more information.

Now, let's look at an example of a JetStream publisher microservice.

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="js_publish",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0
TEST_STREAM = "test_stream"
STREAM_SUBJECTS = [
    "some.js.subject",
]

@app.on_start_task()
async def on_start_task():
    await app.js.add_stream(name=TEST_STREAM, subjects=STREAM_SUBJECTS)
    await app.js.add_consumer(stream=TEST_STREAM, durable_name=TEST_STREAM)

def get_message():
    return {
        "id": app.nats.client.client_id,
    }


@app.timer_task(interval=2)
async def publish_periodically():
    subject = "test.app2.stream"
    message = get_message()
    global NUM
    NUM+=1
    message['counter'] = NUM
    await app.publish(subject=subject, message=message)
    log.info(f"sent {message}")



if __name__ == "__main__":
    app.start()

```
In the example above, we create a Stream using `on_start_task()` to make sure the Stream is created before we start sending messages. Additionally, you have to use the flag `enable_js=True` when initializing a panini app.

Now, let's look at an example of a JetStream push-based consumer microservice.

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_push",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

@app.task()
async def subscribe_to_js_stream_push():
    async def cb(msg):
        log.info(f"got JS message ! {msg.subject}:{msg.data}")

    await app.nats.js_client.subscribe("test.*.stream", cb=cb, durable='consumer-1', stream="sample-stream-1")


if __name__ == "__main__":
    app.start()

```

Finally, here is an example of a JetStream pull-based consumer microservice.

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="js_listen_pull",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger
NUM = 0

def get_message():
    return {
        "id": app.nats.client.client_id,
    }


@app.on_start_task()
async def create_js_staff():
    await app.js.add_stream(name=TEST_STREAM, subjects=STREAM_SUBJECTS)
    await app.js.add_consumer(stream=TEST_STREAM, durable_name=TEST_STREAM, deliver_group='ABC')

@app.task()
async def subscribe_to_js_stream_pull():
    psub = await app.nats.js.pull_subscribe(STREAM_SUBJECTS[0], durable=TEST_STREAM)
    # Fetch and ack messages from consumer.
    for i in range(0, 10):
        msgs = await psub.fetch(1)
        for msg in msgs:
            print(msg.data)
            await msg.ack()

@app.task(interval=1)
async def subscribe_to_js_stream_pull():
    print('some parallel task')



if __name__ == "__main__":
    app.start()

```


At the time of writing, Panini (v0.8.0) does not support key-value storage and other JetStream features. However, with each new version, more features and functionalities are added. Additionally, you can use the `app.nats` object to access directly the underlying [nats.py Client](https://github.com/nats-io/nats.py/blob/0c244c857a15a2af98b3611af795fc2ebc52b2e4/nats/aio/client.py#L178) object.