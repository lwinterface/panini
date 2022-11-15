import asyncio
import time

import nats
from nats import errors
from nats.aio.msg import Msg

from panini import app as panini_app

""" MAKE SURE JETSTREAM ENABLED IN NATS BROKER """


app = panini_app.App(
    service_name="async_js_pull",
    host="127.0.0.1",
    port=4222,
    enable_js=True
)

log = app.logger

@app.listen('execution_system.*.*.balance_updated_event')
async def receive_messages(msg: Msg):
    log.info(f"subject {msg.subject}, got message {msg.data}")



message = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}

TEST_STREAM = "test_stream"
STREAM_SUBJECTS = [
    "some.js.subject",
]
NUM = 0



@app.on_start_task()
async def create_js_staff():
    # await app.js.delete_stream(name=TEST_STREAM)
    await app.js.add_stream(name=TEST_STREAM, subjects=STREAM_SUBJECTS)
    await app.js.add_consumer(stream=TEST_STREAM, durable_name=TEST_STREAM, deliver_group='ABC')



@app.task()
async def start_processing():
    try:
        await asyncio.sleep(5)
        psub = await app.js.pull_subscribe(subject=STREAM_SUBJECTS[0], durable=TEST_STREAM)
        # Fetch and ack messages from consumer.
        while True:
            try:
                msgs = await psub.fetch(100, timeout=1)
            except errors.TimeoutError:
                await asyncio.sleep(1)
                continue
            for msg in msgs:
                try:
                    log.info(f"PULL JS message subject: {msg.subject}, message {msg.data}")
                    await msg.ack()
                except Exception as e:
                    log.exception(e)
                await asyncio.sleep(0.1)
    except Exception as e:
        log.exception("PullSubscribeError: order_trade_event pull_subscribe loop failed!")
        exit()

@app.task(interval=0.5)
async def send_js():
    global NUM
    NUM+=1
    message = {'number': NUM}
    await app.publish_js(subject=STREAM_SUBJECTS[0], stream=TEST_STREAM, message=message)
    log.info(f"JS message sent: {message}")




if __name__ == "__main__":
    app.start()
