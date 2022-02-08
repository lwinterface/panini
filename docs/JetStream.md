Since Panini switched from [asyncio-nats-client](https://pypi.org/project/asyncio-nats-client/) to [nats-py](https://pypi.org/project/nats-py/), it has become possible to support one of the most important features of NATS 2.0 - JetStream.


Core NATS vs NATS Jetstream:

**Core NATS** - default version, stateless messaging, does not guarantee message delivery in certain cases

**NATS JetStream** - is an extension of Core NATS that allows you to store in the broker and replay messages in case of problems.

If this is your first time with JetStream, it is recommended that you familiarize yourself with how it works in NATS:

- https://docs.nats.io/nats-concepts/jetstream
- https://www.byronruth.com/grokking-nats-consumers-part-1/

Panini v0.7.0 does not implement an interface to JetStream at the framework level. Instead, it is suggested to use directly [nats-py](https://pypi.org/project/nats-py/)

Example JetStream publisher microservice:


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


@app.on_start_task()
async def on_start_task():
    await app.nats.js_client.add_stream(name="sample-stream-1", subjects=["test.*.stream"])


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
As you can see in the example, we create a Stream using on_start to make sure the Stream is created before we start sending messages. Also you have to use flag `enable_js=True` when initialize a panini app.

JetStream push-based consumer microservice example:


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

JetStream pull-based consumer microservice example:

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


@app.task()
async def subscribe_to_js_stream_pull():
    psub = await app.nats.js_client.pull_subscribe("test.*.stream", durable='consumer-2')
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


A full-fledged extension of the Panini interface for JetStream is expected in the next versions of Panini.