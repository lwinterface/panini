import asyncio
import time
from panini import app as panini_app

app = panini_app.App(
    service_name="async_sender",
    host="127.0.0.1",
    port=4222,
)
log = app.logger

started_time = None
msg_num = 10
current_msg_num = 0

msg = {
    "key1": "value1",
    "key2": 2,
    "key3": 3.0,
    "key4": [1, 2, 3, 4],
    "key5": {"1": 1, "2": 2, "3": 3, "4": 4, "5": 5},
    "key6": {"subkey1": "1", "subkey2": 2, "3": 3, "4": 4, "5": 5},
    "key7": None,
}


@app.task()
async def request_to_another_topic():
    global started_time
    started_time = time.monotonic()

    def handle_response(msg):
        """Note, that here msg.data will be in bytes"""
        global current_msg_num
        current_msg_num += 1
        log.info(f"MSG: data: {msg.data}, data type: {type(msg.data)}")
        log.info(f"<<<= response num {current_msg_num}")

    for _ in range(msg_num):
        await app.request(
            message=msg, subject="some.topic.to.request", callback=handle_response
        )
        log.info(f"=>>> request num {_}")
    print(f"Sent requests duration = {time.monotonic() - started_time}")
    await app.publish(message={}, subject="finalize.it")


@app.listen("some.topic.to.request")
async def subject_for_requests_listener(msg):
    await asyncio.sleep(1)
    return {"success": True, "data": "request has been processed"}


@app.listen("finalize.it")
async def finalizer(msg):
    while int(current_msg_num) < int(msg_num):
        await asyncio.sleep(0.005)
    duration = time.monotonic() - started_time
    print(f"Handling {msg_num} requests  took: {duration} sec")


if __name__ == "__main__":
    app.start()
