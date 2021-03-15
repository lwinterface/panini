import asyncio
from datetime import datetime

from panini.emulator.event_storage_middleware import EventStorageMiddleware
from panini.app import App

app = App(
    service_name="storage_example",
    host="127.0.0.1",
    port=4222
)


@app.listen("store.listen")
async def listen(message):
    try:
        pass
    except Exception as ex:
        app.logger.exception(message.subject)


@app.listen("store.request")
async def response(message):
    try:
        return {"data": "request"}
    except Exception as ex:
        app.logger.exception(message.subject)


@app.timer_task(interval=2)
async def publish():
    subject = "store.listen"
    try:
        await app.publish(subject, {"data": "publish.data"})
    except Exception as ex:
        app.logger.exception(subject)


@app.task(interval=3)
async def request():
    subject = "store.request"
    try:
        await app.request(subject, {"data": "request.data"})
    except Exception as ex:
        app.logger.exception(subject)


@app.task()
async def request_task():
    for i in range(10):
        subject = "store.request"
        try:
            await app.request(subject, {"data": "request.data"})
            await asyncio.sleep(3)
        except Exception as ex:
            app.logger.exception(subject)


@app.task()
async def publish_task():
    for i in range(10):
        subject = "store.listen"
        try:
            await app.publish(subject, {"data": "publish.data"})
            await asyncio.sleep(2)
        except Exception as ex:
            app.logger.exception(subject)


if __name__ == "__main__":
    app.add_middleware(EventStorageMiddleware, filename=f"resources/events.{datetime.now().strftime('%Y-%m-%d-%H:%M')}.jsonl")
    app.start()
